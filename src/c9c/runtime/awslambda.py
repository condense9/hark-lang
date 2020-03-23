"""AWS Lambda run-time"""


def run_from(handler):
    def _f(event, context):
        linked = compiler.link(
            compiler.compile_all(handler), entrypoint_fn=handler.label
        )
        state = LocalState([event, context])
        machine.run(linked, state)
        return state.ds_pop()

    return _f
