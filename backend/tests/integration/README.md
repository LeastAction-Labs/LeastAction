## How to run integration tests

### MongoDB setup

Run local instance of mongodb and set MONGO_TEST_URI to the connection string of the
new instance inside .env file

If you already have local instance running for the main db, you can always start another. The easiest way to do so is create another config file.
For example:

```
  systemLog:
      destination: file
      path: /opt/homebrew/var/log/mongodb/mongodb-test.log
      logAppend: true
  storage:
      dbPath: /opt/homebrew/var/mongodb-test
  net:
      port: 27018
      bindIp: 127.0.0.1, ::1
      ipv6: true
  replication:
      replSetName: rs0
```

Make sure to have the replication property set and then start the instance using
`mongod --config <path to .conf file>`

OR

Start using Docker: `docker-compose -f docker-compose.test.yml up -d`

The connection string will look something like
`MONGO_TEST_URI=mongodb://localhost:27018?replicaSet=rs0`

### Run tests

Call `uv run pytest tests/integration` to run the whole test suite
