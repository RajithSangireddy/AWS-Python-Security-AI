
def error_handler(error, operation):

    error_code = error.response["Error"]["Code"]
    error_message = error.response["Error"]["Message"]
    raise RuntimeError(f"for the operation {operation}, here is error code: {error_code} and message: {error_message}") from error 