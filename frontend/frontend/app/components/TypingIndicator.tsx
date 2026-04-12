export function TypingIndicator() {
  return (
    <div className="flex max-w-[78%] items-center gap-[5px] rounded-[4px] border border-border-0 bg-bg-1 px-3 py-3">
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="h-[5px] w-[5px] animate-typing-dot rounded-full bg-text-2"
          style={{ animationDelay: `${index * 160}ms` }}
        />
      ))}
    </div>
  );
}
