from src.collector import list_iam_users, list_user_access_keys, get_access_key_usage, normalize_access_key

def collect_aws_iam_inventory(iam):

    iam_inventory = {}
    iam_users = list_iam_users(iam)
    
    #print(iam_users)

    iam_access_keys = []
    for user in iam_users:
        username = user["UserName"]
        iam_access_keys.extend(list_user_access_keys(iam, username))
#why extend, but not append? 
#append will add another list at the end, where as extend will extend that list, like if a user has two keys, it will extend the list and shows both keys
#user1_keys = [{"id": "A"}, {"id": "B"}]
#user2_keys = [{"id": "C"}]
#extend() produces
###[
#    {"id": "A"},
#    {"id": "B"},
#    {"id": "C"}
#]
    #print(iam_access_keys)
    normalized_keys =[]
    for key in iam_access_keys:
        access_key_id = key["AccessKeyId"]
        key_with_usage = key.copy()
        key_with_usage.update(get_access_key_usage(iam, access_key_id))
        
        #print(key_usage)
#here, we have UserName, AccessKeyId, Status, CreateDate AND last_used fields from get_access_key_usage. hence, update() method used to save the last used details on the same dict
#before update()
#{'UserName': 'alice', 'AccessKeyId': 'AKIAEXAMPLE00000001', 'Status': 'Active', 'CreateDate': datetime.datetime(2023, 3, 22, 20, 1, 3, tzinfo=tzutc())}
#after update()
#{'UserName': 'Rajith.Sangireddy', 'AccessKeyId': 'AKIAEXAMPLE00000002',
#        'Status': 'Active', 'CreateDate': datetime.datetime(2019, 12, 26, 15, 46, 47, tzinfo=tzutc()), 
#       'last_used_at': None, 'last_used_service': None, 'last_used_region': None}
# Instead saving it on the iam_access_keys, we are stroing the raw data in the original_key_usage dict for future troubleshooting.
        normalized_keys.append(normalize_access_key(key_with_usage))
        #print(normalized_keys)

    iam_inventory["users"] = iam_users
    iam_inventory["access_keys"] = iam_access_keys
    iam_inventory["normalized_keys"] = normalized_keys

    #print("IAM users:", len(iam_inventory["users"]))
    #print("Raw access keys:", len(iam_inventory["access_keys"]))
    #print("Normalized keys:", len(iam_inventory["normalized_keys"]))
 
    return iam_inventory