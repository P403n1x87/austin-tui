def write_exception_to_file(e):
    import traceback as tb

    trace = "".join(tb.format_tb(e.__traceback__))
    trace += f"{type(e).__qualname__}: {e}"
    # print(trace)
    with open("/tmp/austin-tui.out", "a") as fout:
        fout.write(trace + "\n")


def fp(text):
    with open("/tmp/austin-tui.out", "a") as fout:
        fout.write(str(text) + "\n")


def catch(f):
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception as e:
            write_exception_to_file(e)
            raise e

    return wrapper
