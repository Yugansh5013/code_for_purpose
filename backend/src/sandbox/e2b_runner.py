"""
OmniData — E2B Sandbox Runner (SDK v2)

Executes LLM-generated Python visualization code inside a secure
E2B Code Interpreter sandbox. Returns interactive Plotly JSON
(preferred) or a static PNG fallback as base64.

Compatible with e2b-code-interpreter >= 2.0.0
"""

import base64
import json
import logging
from typing import Optional

from e2b_code_interpreter import AsyncSandbox

logger = logging.getLogger(__name__)

# Sentinel markers for extracting Plotly JSON from stdout
PLOTLY_JSON_START = "__PLOTLY_JSON_START__"
PLOTLY_JSON_END = "__PLOTLY_JSON_END__"

# Sandbox timeout (seconds)
SANDBOX_TIMEOUT = 60


async def run_visualization(
    csv_data: str,
    python_code: str,
    e2b_api_key: str,
) -> dict:
    """
    Execute Python visualization code in an E2B sandbox.

    Args:
        csv_data: CSV string of the dataset to analyze.
        python_code: LLM-generated Python code (Plotly + fallback PNG).
        e2b_api_key: E2B API key for sandbox authentication.

    Returns:
        Dict with:
            - plotly_json: str | None — Plotly figure JSON (preferred)
            - base64_image: str | None — PNG fallback as base64 string
            - stdout: str — raw stdout from execution
            - error: str | None — error message if execution failed
    """
    result = {
        "plotly_json": None,
        "base64_image": None,
        "stdout": "",
        "error": None,
    }

    sandbox = None
    try:
        # ── 1. Create sandbox ────────────────────────────────
        logger.info("E2B: Creating sandbox...")
        sandbox = await AsyncSandbox.create(
            timeout=SANDBOX_TIMEOUT,
            api_key=e2b_api_key,
        )
        logger.info(f"E2B: Sandbox created (id={sandbox.sandbox_id})")

        # ── 2. Upload CSV data ───────────────────────────────
        await sandbox.files.write("/home/user/data.csv", csv_data)
        logger.info(f"E2B: Uploaded data.csv ({len(csv_data)} bytes)")

        # ── 3. Execute Python code ───────────────────────────
        logger.info("E2B: Executing visualization code...")
        execution = await sandbox.run_code(python_code)

        # Capture stdout — v2 returns list of objects with .line attribute
        stdout_text = ""
        if execution.logs and execution.logs.stdout:
            stdout_text = "\n".join(
                log.line if hasattr(log, 'line') else str(log)
                for log in execution.logs.stdout
            )
        result["stdout"] = stdout_text
        
        # Log the sandbox stdout for debugging (shows column inspection, data info)
        if stdout_text:
            # Log non-JSON stdout (skip the huge Plotly JSON blob)
            debug_lines = [line for line in stdout_text.split("\n") if "__PLOTLY_JSON_" not in line and len(line) < 500]
            if debug_lines:
                logger.info(f"E2B stdout (debug):\n{''.join(debug_lines[:20])}")

        # Check for execution errors
        if execution.error:
            error_msg = f"{execution.error.name}: {execution.error.value}"
            if execution.error.traceback:
                error_msg += f"\n{''.join(execution.error.traceback)}"
            result["error"] = error_msg
            logger.warning(f"E2B: Execution error: {error_msg[:200]}")
            return result

        # ── 4. Extract Plotly JSON from stdout ───────────────
        plotly_json = _extract_plotly_json(stdout_text)
        if plotly_json:
            result["plotly_json"] = plotly_json
            logger.info("E2B: Plotly JSON captured successfully")

        # ── 5. Try reading fallback PNG ──────────────────────
        try:
            png_bytes = await sandbox.files.read("/home/user/output.png")
            if png_bytes:
                # png_bytes comes as bytes from E2B
                if isinstance(png_bytes, bytes):
                    result["base64_image"] = base64.b64encode(png_bytes).decode("utf-8")
                elif isinstance(png_bytes, str):
                    result["base64_image"] = base64.b64encode(
                        png_bytes.encode("latin-1")
                    ).decode("utf-8")
                logger.info("E2B: Fallback PNG captured")
        except Exception as png_err:
            logger.debug(f"E2B: No fallback PNG available: {png_err}")

        if not result["plotly_json"] and not result["base64_image"]:
            result["error"] = "No visualization output produced (no Plotly JSON or PNG)"
            logger.warning("E2B: No output captured")

    except Exception as e:
        result["error"] = f"Sandbox error: {str(e)}"
        logger.error(f"E2B: Sandbox error: {e}", exc_info=True)

    finally:
        # ── 6. Always close sandbox ──────────────────────────
        if sandbox:
            try:
                await sandbox.kill()
                logger.info("E2B: Sandbox closed")
            except Exception:
                pass  # Best-effort cleanup

    return result


async def run_visualization_with_retry(
    csv_data: str,
    python_code: str,
    e2b_api_key: str,
    groq_pool: object,
    original_error: Optional[str] = None,
    max_retries: int = 2,
) -> tuple[dict, str]:
    """
    Execute visualization with self-healing retry loop.

    If the sandbox execution fails, feeds the error traceback back
    to the LLM to generate corrected code (up to max_retries).

    Args:
        csv_data: CSV data string.
        python_code: Initial Python code from LLM.
        e2b_api_key: E2B API key.
        groq_pool: Groq client pool for LLM retries.
        original_error: Pre-existing error to fix (if any).
        max_retries: Maximum retry attempts.

    Returns:
        Tuple of (result_dict, final_python_code)
    """
    current_code = python_code

    for attempt in range(max_retries + 1):
        result = await run_visualization(csv_data, current_code, e2b_api_key)

        # Success — either Plotly JSON or base64 image
        if result["plotly_json"] or result["base64_image"]:
            logger.info(f"E2B: Visualization succeeded on attempt {attempt + 1}")
            return result, current_code

        # Failure — try to self-heal
        if attempt < max_retries and result["error"]:
            logger.info(
                f"E2B: Attempt {attempt + 1} failed, requesting LLM fix "
                f"({max_retries - attempt} retries left)"
            )
            try:
                current_code = await _fix_code_with_llm(
                    groq_pool=groq_pool,
                    broken_code=current_code,
                    error_trace=result["error"],
                )
            except Exception as fix_err:
                logger.warning(f"E2B: LLM fix failed: {fix_err}")
                break
        else:
            break

    return result, current_code


def _extract_plotly_json(stdout: str) -> Optional[str]:
    """
    Extract Plotly JSON from stdout using sentinel markers.

    The Data Scientist prompt instructs the LLM to wrap the JSON:
        print("__PLOTLY_JSON_START__")
        print(json.dumps(fig_json))
        print("__PLOTLY_JSON_END__")
    """
    if PLOTLY_JSON_START not in stdout:
        return None

    try:
        start_idx = stdout.index(PLOTLY_JSON_START) + len(PLOTLY_JSON_START)
        end_idx = stdout.index(PLOTLY_JSON_END)
        json_str = stdout[start_idx:end_idx].strip()

        # Validate it's actually valid JSON
        parsed = json.loads(json_str)

        # Verify it has Plotly structure (data + layout)
        if "data" in parsed or isinstance(parsed, list):
            return json_str

        logger.warning("E2B: JSON parsed but doesn't look like Plotly figure")
        return None

    except (ValueError, json.JSONDecodeError) as e:
        logger.warning(f"E2B: Failed to parse Plotly JSON: {e}")
        return None


async def _fix_code_with_llm(
    groq_pool: object,
    broken_code: str,
    error_trace: str,
) -> str:
    """
    Ask the LLM to fix broken Python code given the error traceback.
    """
    FIX_PROMPT = """You are a Python debugging expert. The following code failed
with the error shown below. Fix the code and return ONLY the corrected Python code.
Do not include explanations or markdown markers.

## Broken Code:
```python
{code}
```

## Error:
{error}

## Instructions:
- Fix the error while preserving the original intent
- Keep all imports and file paths the same
- Ensure the Plotly JSON output markers are preserved
- Output ONLY valid Python code, nothing else"""

    response = groq_pool.complete_with_retry(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You fix Python code. Return ONLY corrected code."},
            {
                "role": "user",
                "content": FIX_PROMPT.format(
                    code=broken_code[:3000],
                    error=error_trace[:1500],
                ),
            },
        ],
        temperature=0.0,
        max_tokens=2000,
    )

    fixed = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    fixed = fixed.replace("```python", "").replace("```", "").strip()

    # Strip <think> blocks if present
    if "<think>" in fixed:
        parts = fixed.split("</think>")
        fixed = parts[-1].strip() if len(parts) > 1 else fixed

    logger.info(f"E2B: LLM produced fix ({len(fixed)} chars)")
    return fixed
