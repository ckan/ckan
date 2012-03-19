===========
Task Status
===========

The Task Status domain object is essentially a key/value store that is used by
CKAN Tasks to store the results of each processing task.

Schema
======

Each task status entry consists of the following required fields:

* **id** [UnicodeText]: A unique ID for each status object. Automatically generated if not provided.
* **entity_id** [UnicodeText]:  Each task_status entry is assumed to be information about a task that performs some operation on another CKAN domain object (usually either a dataset/package or a resource). This refers to the ID of that object.
* **entity_type** [UnicodeText]: The type of CKAN domain object that the task operates on (eg: resource).
* **task_type** [UnicodeText]: The type of CKAN Task (eg: qa, webstorer, archiver, etc).
* **key** [UnicodeText]: Key descriptor for data being stored.
* **value** [UnicodeText]: Actual data being stored.

.. note:: each task status entry must be unique on *(entity_id, task_type, key)*.

They also contain a number of optional fields:

* **state** [UnicodeText]: The current (or final) state of the task.
* **error** [UnicodeText]: Information about any error that occurred during processing.
* **last_updated** [DateTime]: The time at which this entry was last updated. Defaults to the current time.

