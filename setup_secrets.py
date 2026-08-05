"""
One-time setup script: creates the Databricks secret scope and stores the
Lakebase connection URL for this assignment. Run this locally (with the
Databricks CLI configured) or from a notebook — never commit the resulting
secret value anywhere. Re-runnable: updates the stored URL in place.

Usage:
    python setup_secrets.py
"""
import getpass

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import ResourceAlreadyExists
from databricks.sdk.service import workspace

SCOPE = "assignment1-support-tickets"
KEY = "lakebase-url"

w = WorkspaceClient()

try:
    w.secrets.create_scope(scope=SCOPE)
except ResourceAlreadyExists:
    pass

w.secrets.put_secret(
    scope=SCOPE,
    key=KEY,
    string_value=getpass.getpass("Paste your Lakebase URL: "),
)

w.secrets.put_acl(
    scope=SCOPE,
    principal="users",
    permission=workspace.AclPermission.READ,
)
