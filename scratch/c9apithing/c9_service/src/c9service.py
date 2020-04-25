import c9.controllers.ddb
import c9.executors.awslambda

# There is no python in this lambda. All user code is a layer above.
# There are no C9 files in this lambda. All programs are stored in DynamoDB.

# Model: session_id 0 is special, it contains the "base" executable, used for
# new sessions. When a session is created, it gets a copy of the base
# executable. So it can be modified without affecting already running sessions.
#
# A session: an execution/evaluation session, may involve multiple machines.


def def_(event, context):
    raise NotImplementedError


def importpy(event, context):
    raise NotImplementedError


def callf(event, context):
    raise NotImplementedError
    # Event must contain the function to call, and the args


def resume(event, context):
    raise NotImplementedError



# def {FN_HANDLE_EXISTING}(event, context):
#     run_method = c9.controllers.ddb.run_existing
#     return c9.executors.awslambda.handle_existing(run_method, event, context)

# def {FN_HANDLE_NEW}(event, context):
#     run_method = c9.controllers.ddb.run
#     return c9.executors.awslambda.handle_new(run_method, event, context)
