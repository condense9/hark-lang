@my_dataclass
class Persistent:
    """Data persistent after a session is over"""

    executable: Executable
    core_dump: Core
    result: Any


class Core:
    """Data required while a session is running"""

    def push_frame
    def pop_frame

    def

    def write_stdout(self, vmid, data): pass




# What are the data objects I need to store?
# - standard output (list, shared by all threads)
# - thread state (dict per thread)
# - future data (per thread)
# - probe data (per thread)
# - activation records (shared, heap-style)
# - session data (machine count, stopped, etc)


# What are the kinds of operations I need to do *while running*?
# - write_stdout
# -

# Stdout (shared)
# - append item (atomic)

# Probe (not shared)
# - append logs, events

# Thread state (not shared)
# - get state
# - set state

# Future data (shared)
# - check if resolved
# - resolve

# Activation Record
# - new
# - get_count
# - set
# - destroy
# -


# Data Types
# - list
# - dict

# Operations
# - append
# - check_and_set (update)
# - set


# Efficient activation records
# - tricky.
# - every AR might have dependent threads. So they need sync.
# - They could be marked/labelled? So most of them can be pushed/popped without
#   worrying


@dataclass
class Session:
    thread_idx: int
    arec_idx: int
    stopped: bool
    broken: bool
    # trigger:
    # inputs:
    # executable: Executable
    result = None


class ThreadError:
    message:
    traceback:

class ThreadData:
    probe:
    state:
    error:
    future:

class Persistent:
    stdout: List
    threads: List[ThreadData]


class SessionRuntime:
    session_id: str

    def set_meta
    def write_stdout

    def new_thread
    def get_state
    def set_state
    def get_probe
    def set_probe
    def get_future
    def set_future
    def set_error

    def new_arec
    def get_arec
    def set_arec


@dataclass
class Item:
    _item_id: str
    # def asdict


class Future(Item):
    resolved: bool


class State(Item):
    stopped: bool


class Thread(Item):
    future_id:
    state_id:


class:
    def new(self, item_type)
    def get(self, item: Item, *more_items)
    def set(self, item: Item, *more_items)
    def gls(self, item: Item)  # get, lock, save (contextmgr)


# per session:
# meta        | one, HASH                      | session:ID:meta
# stdout      | many, HASH (append only)       | session:ID:stdout:ID
# probe_log   | many, HASH (append only)       | session:ID:plog:ID
# probe_event | many, HASH (append only)       | session:ID:pevent:ID
# arec        | many, HASH (add/remove/update) | session:ID:arec:ID
# future      | many, HASH (update)            | session:ID:future:THREAD_ID
# state       | many, HASH (update).           | session:ID:state:THREAD_ID
# error       | many, HASH (add/update).       | session:ID:state:THREAD_ID


# Meta (book-keeping):
# - num probe_logs
# - num probe_events
# - num arecs
# - num threads
# - stopped
# - thread_exit_status (LIST bool)


class Storage:
    def __init__(session_id)

    # stdout, logs and events all stored together conceptually. The objects
    # contain the thread id
    def add_stdout(item)
    def add_probe_log(log)
    def add_probe_event(event)

    def new_thread() -> int

    def get_state(thread_id) -> State
    def write_state(thread_id, state)

    def get_future(thread_id) -> Future
    def lock_future(thread_id)  # context mgr
    def set_future(thread_id, future)
    def add_continuation(thread_id, waiter_id)

    def new_arec() -> int
    def get_arec(arec_id) -> ActivationRecord
    def lock_arec(arec_id)  # context mgr
    def set_arec(arec_id)
    def delete_arec(arec_id)
    def increment_ref(arec_id)  # must guarantee increment
    def decrement_ref(arec_id) -> int  # must guarantee decrement

    def get_stdout() -> List
    # ...

    def stop(finished_ok)


class Controller:
    def get_state
