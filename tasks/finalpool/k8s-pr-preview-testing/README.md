The model needs to start a NodePort service (instead of the previously used ClusterIP), so that the application can be accessed externally.
There is a concern that the required port is currently hardcoded to 30123. Hopefully, this will not cause any issues.
