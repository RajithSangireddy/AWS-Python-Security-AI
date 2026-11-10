
from botocore.exceptions import BotoCoreError
from src.error_handler import error_handler

def list_iam_users(iam):
    #iam = session.client("iam")
    users =[]
    try:
        paginator = iam.get_paginator("list_users")
        pages = paginator.paginate()

        # the pages is dictionary
        
        #for page in pages:
        #    print("Page type:", type(page))
        #    print("Page fields:", page.keys())
        #    print("Users type:", type(page["Users"]))
        #    print("Users count:", len(page["Users"]))
        #users =[]   it's best practise to add before try block.
        for page in pages:
                                ###
                                # the page is dictionary and will be like this after AWS returns the user data
                                # page = {
                                #         "Users": [
                                #                  {"UserName": "alice"},
                                #                  {"UserName": "bob"}                
                                #                   ],
                                #          "istruncated" : false
                                #        }
                                ###
            for user in page["Users"]:
                #fetching the first element from the list of dictionaries in this case Users which is another dictionary
                users.append(user)
                print(f"Here is the username: {user['UserName']}" )
    
    except ClientError as error:
        error_handler(error, "list_users")

    except BotoCoreError as error:
        raise RuntimeError(f"AWS SDK error: {error}") from error

    return users


def list_user_access_keys(iam, username):
    iam_keys = []
    try: 
        paginator = iam.get_paginator("list_access_keys")
        pages = paginator.paginate(UserName=username)

        
        for page in pages:
            for keys in page["AccessKeyMetadata"]:
                iam_keys.append(keys)
                #print(f"here is access key Id: {keys['AccessKeyId']} and it is {keys['Status']}")

    except ClientError as error:
        error_handler(error, "list_access_keys")

    except BotoCoreError as error:
        raise RuntimeError(f"AWS SDK error: {error}") from error

    return iam_keys


def get_access_key_usage(iam, access_key_id):
    last_used_details = {}
    try:
        response = iam.get_access_key_last_used(AccessKeyId=access_key_id) # it returns a dict
        usage = response["AccessKeyLastUsed"]  # this also returns a dictionary
        last_used_date = usage.get("LastUsedDate") 
        last_used_service = usage.get("ServiceName")
        last_used_region = usage.get("Region")
        ## the above is similar to usage["LastUsedDate"] this, but if the key was not used, this will throw keyError, hence, we used .get
        
        last_used_details["last_used_at"] = last_used_date
        
        if last_used_service == "N/A":
            last_used_details["last_used_service"] = None
        else:
            last_used_details["last_used_service"] = last_used_service

        if last_used_region == "N/A":
            last_used_details["last_used_region"] = None
        else:
            last_used_details["last_used_region"] = last_used_region

    except ClientError as error:
        error_handler(error, "get_access_key_last_used")

    except BotoCoreError as error:
        raise RuntimeError(f"AWS SDK error: {error}") from error
 
    return last_used_details


def normalize_access_key(key):
    normalized_key = {
        "username" : key.get("UserName"),
        "access_key_id" : key.get("AccessKeyId"),
        "status"  : key.get("Status"),
        "created_at" : key.get("CreateDate"),
        "last_used_at" : key.get("last_used_at"),
        "last_used_service" : key.get("last_used_service"),
        "last_used_region" : key.get("last_used_region")
    }
    #print(f"here is normalized key : {normalized_key}")
    return normalized_key
    
