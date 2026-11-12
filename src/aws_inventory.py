from src.collector import list_iam_users, list_user_access_keys, get_access_key_usage, normalize_access_key,list_iam_roles,normalize_role_trust_policy

def collect_aws_iam_inventory(iam):

    iam_inventory = {}
    iam_access_keys = []

    iam_users = list_iam_users(iam)

    for user in iam_users:
        username = user["UserName"]
        iam_access_keys.extend(list_user_access_keys(iam, username))
#why extend, but not append? refer the docs/03-aws-inventory.md file
    #print(iam_access_keys)
    normalized_keys =[]
    for key in iam_access_keys:
        access_key_id = key["AccessKeyId"]
        key_with_usage = key.copy()

        key_with_usage.update(get_access_key_usage(iam, access_key_id))
        #print(key_with_usage)
        normalized_keys.append(normalize_access_key(key_with_usage))

    normalized_roles = []
    iam_roles = list_iam_roles(iam)
    for role in iam_roles:
        normalized_roles.append(normalize_role_trust_policy(role))

    iam_inventory["users"] = iam_users
    iam_inventory["access_keys"] = iam_access_keys
    iam_inventory["normalized_keys"] = normalized_keys
    iam_inventory["roles"] = iam_roles
    iam_inventory["normalized_roles"] = normalized_roles


    #print("IAM users:", len(iam_inventory["users"]))
    #print("Raw access keys:", len(iam_inventory["access_keys"]))
    #print("Normalized keys:", len(iam_inventory["normalized_keys"]))

    return iam_inventory