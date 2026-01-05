# Ajouter cette classe pour résoudre le conflit avec YOLOv5
class TryExcept:
    """
    TryExcept class for YOLOv5 compatibility.
    Usage: @TryExcept() decorator or 'with TryExcept():' context manager
    """
    def __init__(self, msg=''):
        self.msg = msg

    def __call__(self, func):
        def handler(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"{self.msg} {e}")
        return handler

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            print(f"{self.msg} {exc_val}")
        return True
