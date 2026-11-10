# %%
import os
import sys

print("Current working directory:", os.getcwd())
print("Python executable:", sys.executable)
print("Python import paths:", sys.path)


from src.auth import create_aws_session
from src.collector import list_iam_users, list_user_access_keys, get_access_key_usage, normalize_access_key

session = create_aws_session("security-audit")
iam = session.client("iam")

iam_users = list_iam_users(iam)

print(f"Total IAM users: {len(iam_users)} ")

#####print(f" {iam_users}")

iam_access_keys = []
normalized_keys =[]
for user in iam_users:
    username = user["UserName"]
    iam_access_keys.extend(list_user_access_keys(iam, username))
     
print(f"Total access keys: {len(iam_access_keys)}")

#print(iam_access_keys)
#here, we have UserName, AccessKeyId, Status, and CreateDate in the each dictionay within the list.
#key_usage = [] with the update, we are updating the iam_access_key list with key details along with the usage details.
for key in iam_access_keys:
   access_key_id = key["AccessKeyId"]
   key_with_usage = key.copy()
   key_with_usage.update(get_access_key_usage(iam, access_key_id))
   
  #key.update(get_access_key_usage(iam, access_key_id))
#here, we have UserName, AccessKeyId, Status, CreateDate AND last_used fields from usage. hence, update() method used.
# Instead saving it on the iam_access_keys, we are stroing the raw data in the original_key_usage dict for future troubleshooting.
   normalized_keys.append(normalize_access_key(key_with_usage))
#print(iam_access_keys)
#print("Total keys:", len(iam_access_keys))
#print("First key fields:", iam_access_keys[0].keys())
#print("Last used:", iam_access_keys[0]["last_used_at"])

