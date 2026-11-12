# %%
import os
import sys

print("Current working directory:", os.getcwd())
#print("Python executable:", sys.executable)
#print("Python import paths:", sys.path)

from pprint import pprint
from src.auth import create_aws_session
from src.collector import list_iam_users, list_user_access_keys, get_access_key_usage, normalize_access_key, list_iam_roles, normalize_role_trust_policy
from src.aws_inventory import collect_aws_iam_inventory

session = create_aws_session("security-audit")
iam = session.client("iam")

iam_inventory = collect_aws_iam_inventory(iam)

#pprint(iam_inventory)
