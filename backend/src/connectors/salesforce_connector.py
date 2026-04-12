"""
OmniData — Salesforce Connector

Real Salesforce API client using simple_salesforce.
Connects to the Salesforce Developer Edition org with OAuth credentials.
Provides SOQL query execution and object schema introspection.

This connector is used:
1. At seed time — to push CRM records into the live Salesforce org
2. At runtime — as a live data source alongside the Pinecone vector cache

Environment variables required:
    SALESFORCE_USERNAME, SALESFORCE_PASSWORD,
    SALESFORCE_SECURITY_TOKEN, SALESFORCE_INSTANCE_URL
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SalesforceConnector:
    """
    Live Salesforce API connector.
    
    Authenticates via username/password + security token flow.
    Provides SOQL query execution and basic object metadata.
    """

    def __init__(
        self,
        username: str = None,
        password: str = None,
        security_token: str = None,
        instance_url: str = None,
    ):
        self.username = username or os.getenv("SALESFORCE_USERNAME", "")
        self.password = password or os.getenv("SALESFORCE_PASSWORD", "")
        self.security_token = security_token or os.getenv("SALESFORCE_SECURITY_TOKEN", "")
        self.instance_url = instance_url or os.getenv("SALESFORCE_INSTANCE_URL", "")
        self._sf = None

    def connect(self) -> bool:
        """
        Establish connection to Salesforce org.
        Returns True if successful, False otherwise.
        """
        try:
            from simple_salesforce import Salesforce

            self._sf = Salesforce(
                username=self.username,
                password=self.password,
                security_token=self.security_token,
                instance_url=self.instance_url,
            )
            # Verify connection by fetching org info
            org_id = self._sf.sf_instance
            logger.info(f"Salesforce connected: {org_id}")
            return True

        except Exception as e:
            logger.error(f"Salesforce connection failed: {e}")
            self._sf = None
            return False

    @property
    def is_connected(self) -> bool:
        return self._sf is not None

    def query(self, soql: str) -> list[dict]:
        """
        Execute a SOQL query and return results as a list of dicts.
        
        Args:
            soql: Valid SOQL query string
            
        Returns:
            List of record dicts (OrderedDict stripped to regular dict)
        """
        if not self._sf:
            raise ConnectionError("Salesforce not connected. Call connect() first.")

        try:
            result = self._sf.query_all(soql)
            records = []
            for record in result.get("records", []):
                # Strip the Salesforce metadata wrapper
                clean = {k: v for k, v in record.items() if k != "attributes"}
                records.append(clean)

            logger.info(f"SOQL query returned {len(records)} records")
            return records

        except Exception as e:
            logger.error(f"SOQL query failed: {e}")
            raise

    def describe_object(self, object_name: str) -> dict:
        """
        Get object metadata (fields, labels, types).
        
        Args:
            object_name: Salesforce object API name (e.g., 'Account')
            
        Returns:
            Dict with object metadata including field descriptions
        """
        if not self._sf:
            raise ConnectionError("Salesforce not connected. Call connect() first.")

        try:
            obj = getattr(self._sf, object_name)
            desc = obj.describe()
            
            fields = []
            for f in desc.get("fields", []):
                fields.append({
                    "name": f["name"],
                    "label": f["label"],
                    "type": f["type"],
                    "custom": f.get("custom", False),
                })

            return {
                "name": desc["name"],
                "label": desc["label"],
                "field_count": len(fields),
                "fields": fields,
            }

        except Exception as e:
            logger.error(f"Object describe failed for {object_name}: {e}")
            raise

    def test_connection(self) -> dict:
        """
        Test connectivity and return org info.
        
        Returns:
            Dict with instance, org_id, and user info
        """
        if not self._sf:
            return {"connected": False, "error": "Not connected"}

        try:
            identity = self._sf.restful("", method="GET")
            return {
                "connected": True,
                "instance": self._sf.sf_instance,
                "username": self.username,
                "org_type": "Developer Edition",
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def upsert_accounts(self, accounts: list[dict]) -> int:
        """
        Upsert Account records into Salesforce.
        
        Args:
            accounts: List of Account dicts with field values
            
        Returns:
            Number of records successfully upserted
        """
        if not self._sf:
            raise ConnectionError("Salesforce not connected.")

        count = 0
        for acc in accounts:
            try:
                self._sf.Account.create(acc)
                count += 1
            except Exception as e:
                logger.warning(f"Account upsert failed for {acc.get('Name')}: {e}")

        logger.info(f"Upserted {count}/{len(accounts)} accounts to Salesforce")
        return count

    def upsert_opportunities(self, opportunities: list[dict], account_map: dict) -> int:
        """
        Upsert Opportunity records, linking to Account IDs.
        
        Args:
            opportunities: List of Opportunity dicts
            account_map: Mapping of AccountName -> Salesforce AccountId
            
        Returns:
            Number of records successfully upserted
        """
        if not self._sf:
            raise ConnectionError("Salesforce not connected.")

        count = 0
        for opp in opportunities:
            try:
                record = {k: v for k, v in opp.items() if k != "AccountName"}
                account_name = opp.get("AccountName", "")
                if account_name in account_map:
                    record["AccountId"] = account_map[account_name]
                self._sf.Opportunity.create(record)
                count += 1
            except Exception as e:
                logger.warning(f"Opportunity upsert failed for {opp.get('Name')}: {e}")

        logger.info(f"Upserted {count}/{len(opportunities)} opportunities to Salesforce")
        return count

    def upsert_cases(self, cases: list[dict], account_map: dict) -> int:
        """
        Upsert Case records, linking to Account IDs.
        
        Args:
            cases: List of Case dicts
            account_map: Mapping of AccountName -> Salesforce AccountId
            
        Returns:
            Number of records successfully upserted
        """
        if not self._sf:
            raise ConnectionError("Salesforce not connected.")

        count = 0
        for case in cases:
            try:
                record = {k: v for k, v in case.items() if k != "AccountName"}
                account_name = case.get("AccountName", "")
                if account_name in account_map:
                    record["AccountId"] = account_map[account_name]
                self._sf.Case.create(record)
                count += 1
            except Exception as e:
                logger.warning(f"Case upsert failed for {case.get('Subject')}: {e}")

        logger.info(f"Upserted {count}/{len(cases)} cases to Salesforce")
        return count
