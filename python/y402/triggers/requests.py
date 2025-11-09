from y402.core.types.errors import ConditionalDependencyError

try:
    import requests
except ImportError:
    raise ConditionalDependencyError("Requests library is not installed. Install it as a requirement "
                                     "by invoking requests==2.32.5 or similar")