import boto3
from botocore.exceptions import ProfileNotFound
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import InvalidConfigError
from botocore.exceptions import ClientError

def create_aws_session(name_of_profile: str):

    try:
        session = boto3.Session(profile_name=name_of_profile)
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        print(f"AWS Account : {identity['Account']}")
        print(f"Role ARN is : {identity.get('Arn')}")

    except ProfileNotFound as error:
        raise RuntimeError("AWS profile not found") from error

    except InvalidConfigError as error:
        raise RuntimeError("AWS profile or role configuration is invalid") from error

    except NoCredentialsError as error:
        raise RuntimeError("AWS credentials not available") from error
    
    except ClientError as error:
        error_code = error.response["Error"]["Code"]
        raise RuntimeError(f"AWS API request failed: {error_code}") from error

    return session