1. Authentication
    The base URL for API on Server calls is: http(s)://SERVER[:PORT]/[CONTEXT]/rest/rtm/1.0/api In order to make REST requests to Jira Server, use basic authentication described on Atlassian’s website. In Postman choose Basic Authentication and login with Username and Password. It can be a dedicated user with proper permissions, created in Jira especially for REST API purposes:


2. Requirements
    Requirements module gathers the descriptions and expectations of all the functionalities which the final product must fulfill in order to be considered useful and ready for release.

    How to set up links
    Operation SET - generates an exact set of links indicated in the payload

    {
    "coveredTestCases": {
        "set": [
        {
            "testKey": "{{TcTestKey2}}"
        }
        ]
    }
    }
    
    Operation ADD - adds links indicated in the payload

    {
    "coveredTestCases": {
        "add": [
        {
            "testKey": "{{TcTestKey2}}"
        }
        ]
    }
    }
    
    Operation REMOVE - deletes links indicated in the payload

    {
    "coveredTestCases": {
        "remove": [
        {
            "testKey": "{{TcTestKey2}}"
        }
        ]
    }
    }
    Copy
    Note
        In case of leaving the SET/ADD/REMOVE playload empty, the set operation will be applied. It means that:
        - links which are not defined in the new playload will be removed
        - existing links will stay the same
        - new links will be added.


    - GET ​/api​/requirement​/{testKey} : Get requirement
        Success Responses Example
            {
            "issueTypeId": 123,
            "epicName": "Epic name",
            "projectKey": "KEY-1",
            "summary": "Example of a summary.",
            "description": "Example of a description.",
            "assigneeId": "12345678901234",
            "parentTestKey": "KEY-1",
            "testKey": "KEY-1",
            "priority": {
                "id": 10000,
                "name": "High"
            },
            "status": {
                "id": 123,
                "statusName": "name"
            },
            "labels": [
                "label1",
                "label2",
                "label3"
            ],
            "components": [
                {
                "id": 1
                },
                {
                "id": "2"
                },
                {
                "id": "3"
                }
            ],
            "versions": [
                {
                "id": "1"
                },
                {
                "id": "2"
                },
                {
                "id": "3"
                }
            ],
            "timeEstimate": "5h 30m",
            "testCasesCovered": [
                {
                "testKey": "KEY-1",
                "issueId": 123
                }
            ],
            "allFields": {
                "additionalProp1": {},
                "additionalProp2": {},
                "additionalProp3": {}
            }
            }


    - PUT ​/api​/requirement​/{testKey} : Update requirement
        Request body
        application/json
            Example Value
            Schema
            {
            "issueTypeId": 123,
            "epicName": "Epic name",
            "summary": "Example of a summary.",
            "description": "Example of a description.",
            "assigneeId": "12345678901234",
            "parentTestKey": "KEY-1",
            "testKey": "KEY-1",
            "priority": {
                "id": 10000,
                "name": "High"
            },
            "labels": [
                "label1",
                "label2",
                "label3"
            ],
            "components": [
                {
                "id": 1
                },
                {
                "id": "2"
                },
                {
                "id": "3"
                }
            ],
            "versions": [
                {
                "id": "1"
                },
                {
                "id": "2"
                },
                {
                "id": "3"
                }
            ],
            "timeEstimate": "5h 30m",
            "executeTransition": {
                "id": 123,
                "name": "name"
            },
            "testCasesCovered": [
                {
                "testKey": "KEY-1",
                "issueId": 123
                }
            ]
            }

    - DELETE ​/api​/requirement​/{testKey} : Delete requirement.

    - POST ​/api​/requirement : Create requirement
        Request body
            application/json
            Example Value
            Schema
            {
            "issueTypeId": 123,
            "epicName": "Epic name",
            "projectKey": "KEY-1",
            "summary": "Example of a summary.",
            "description": "Example of a description.",
            "assigneeId": "12345678901234",
            "parentTestKey": "KEY-1",
            "testKey": "KEY-1",
            "priority": {
                "id": 10000,
                "name": "High"
            },
            "status": {
                "id": 123,
                "statusName": "name"
            },
            "labels": [
                "label1",
                "label2",
                "label3"
            ],
            "components": [
                {
                "id": 1
                },
                {
                "id": "2"
                },
                {
                "id": "3"
                }
            ],
            "versions": [
                {
                "id": "1"
                },
                {
                "id": "2"
                },
                {
                "id": "3"
                }
            ],
            "timeEstimate": "5h 30m",
            "testCasesCovered": [
                {
                "testKey": "KEY-1",
                "issueId": 123
                }
            ]
            }


3. Test Case
    Test Case is a step-by-step procedure, where the testing path is defined. Test Case determines activities that should be taken to cover Requirement. Each Test Case is only a template before it’s executed by the testers.

    Note
    While referring to a Test Case, Test Plan and Test Execution, make sure you properly defined their names:
    TEST_CASES
    TEST_PLANS
    TEST_EXECUTIONS

    How to set up links
    Operation SET - generates an exact set of links indicated in the payload

    {
    "coveredRequirements": {
        "set": [
        {
            "testKey": "{{ReqTestKey2}}"
        }
        ]
    }
    }

    Operation ADD - adds links indicated in the payload

    {
    "coveredRequirements": {
        "add": [
        {
            "testKey": "{{ReqTestKey2}}"
        }
        ]
    }
    }

    Operation REMOVE - deletes links indicated in the payload

    {
    "coveredRequirements": {
        "remove": [
        {
            "testKey": "{{ReqTestKey2}}"
        }
        ]
    }
    }

    Note
        In case of leaving the SET/ADD/REMOVE playload empty, the set operation will be applied. It means that:
        - links which are not defined in the new playload will be removed
        - existing links will stay the same
        - new links will be added.


    V1 API

        Note
        Starting from RTM 6.0 version, we recommend you to use V2 API. We still support V1 API in older RTM releases.

    - GET ​/api​/test-case​/{testKey} : Get test case
        Success Responses
            Example Value
            Schema
            {
            "stepGroups": [
                {
                "id": 123,
                "name": "Default group",
                "linkedFromId": 123,
                "ordinal": 1,
                "steps": [
                    {
                    "id": 123,
                    "ordinal": 1,
                    "stepColumns": [
                        {
                        "id": 123,
                        "columnId": 1,
                        "ordinal": 1,
                        "value": "Example value",
                        "name": "Actions"
                        }
                    ],
                    "stepAttachments": [
                        {
                        "attachmentId": 123,
                        "attachmentMetadataUrl": "https://example.com"
                        }
                    ]
                    }
                ]
                }
            ],
            "projectKey": "KEY-1",
            "summary": "Example of a summary.",
            "description": "Example of a description.",
            "assigneeId": "12345678901234",
            "parentTestKey": "KEY-1",
            "testKey": "KEY-1",
            "priority": {
                "id": 10000,
                "name": "High"
            },
            "status": {
                "id": 123,
                "statusName": "name"
            },
            "labels": [
                "label1",
                "label2",
                "label3"
            ],
            "components": [
                {
                "id": 1
                },
                {
                "id": "2"
                },
                {
                "id": "3"
                }
            ],
            "versions": [
                {
                "id": "1"
                },
                {
                "id": "2"
                },
                {
                "id": "3"
                }
            ],
            "timeEstimate": "5h 30m",
            "environment": "Chrome",
            "preconditions": "Check your project configuration before the test.",
            "coveredRequirements": [
                {
                "testKey": "KEY-1",
                "issueId": 123
                }
            ],
            "allFields": {
                "additionalProp1": {},
                "additionalProp2": {},
                "additionalProp3": {}
            }
            }

    - PUT ​/api​/test-case​/{testKey} : Update test case
        Request body
                application/json
                Example Value
                Schema
                {
                "projectKey": "KEY-1",
                "summary": "Example of a summary.",
                "description": "Example of a description.",
                "assigneeId": "12345678901234",
                "parentTestKey": "KEY-1",
                "testKey": "KEY-1",
                "priority": {
                    "id": 10000,
                    "name": "High"
                },
                "status": {
                    "id": 123,
                    "statusName": "name"
                },
                "labels": [
                    "label1",
                    "label2",
                    "label3"
                ],
                "components": [
                    {
                    "id": 1
                    },
                    {
                    "id": "2"
                    },
                    {
                    "id": "3"
                    }
                ],
                "versions": [
                    {
                    "id": "1"
                    },
                    {
                    "id": "2"
                    },
                    {
                    "id": "3"
                    }
                ],
                "timeEstimate": "5h 30m",
                "environment": "Chrome",
                "preconditions": "Check your project configuration before the test.",
                "steps": [
                    [
                    {
                        "value": "Text value",
                        "groupName": "Group name"
                    }
                    ]
                ],
                "coveredRequirements": [
                    {
                    "testKey": "KEY-1",
                    "issueId": 123
                    }
                ]
                }
            Responses
            Code	Description
            200
            Success
            application/json
            Example Value
            Schema
            [
            "string"
            ]

    - DELETE ​/api​/test-case​/{testKey} : Delete test case

    - POST ​/api​/test-case : Create test case
            Request body
            application/json
            Example Value
            Schema
            {
            "projectKey": "KEY-1",
            "summary": "Example of a summary.",
            "description": "Example of a description.",
            "assigneeId": "12345678901234",
            "parentTestKey": "KEY-1",
            "testKey": "KEY-1",
            "priority": {
                "id": 10000,
                "name": "High"
            },
            "status": {
                "id": 123,
                "statusName": "name"
            },
            "labels": [
                "label1",
                "label2",
                "label3"
            ],
            "components": [
                {
                "id": 1
                },
                {
                "id": "2"
                },
                {
                "id": "3"
                }
            ],
            "versions": [
                {
                "id": "1"
                },
                {
                "id": "2"
                },
                {
                "id": "3"
                }
            ],
            "timeEstimate": "5h 30m",
            "environment": "Chrome",
            "preconditions": "Check your project configuration before the test.",
            "steps": [
                [
                {
                    "value": "Text value",
                    "groupName": "Group name"
                }
                ]
            ],
            "coveredRequirements": [
                {
                "testKey": "KEY-1",
                "issueId": 123
                }
            ]
            }

            Responses
            Code	Description
            200
            Success

            Media type

            application/json
            Controls Accept header.
            Example Value
            Schema
            {
            "issueId": 10001,
            "issueKey": "TES-1",
            "testKey": "TES-1",
            "summary": "Example of a summary.",
            "self": "string",
            "warnings": [
                "string"
            ]
            }



4. Test Plan
    Before the actual testing process starts, a Test Plan with all related Test Cases listed in it must be created by the team members. It means that Test Plans summarize all actions which must be done in order to check the functionality of a particular feature.

    Note
    While referring to a Test Case, Test Plan and Test Execution, make sure you properly defined their names:
    TEST_CASES
    TEST_PLANS
    TEST_EXECUTIONS

    How to set up links
    Operation SET - generates an exact set of links indicated in the payload

    {
    "includedTestCases": {
        "set": [
        {
            "testKey": "{{TcTestKey2}}"
        }
        ]
    }
    }
    Copy
    Operation ADD - adds links indicated in the payload

    {
    "includedTestCases": {
        "add": [
        {
            "testKey": "{{TcTestKey2}}"
        }
        ]
    }
    }
    Copy
    Operation REMOVE - deletes links indicated in the payload

    {
    "includedTestCases": {
        "remove": [
        {
            "testKey": "{{TcTestKey2}}"
        }
        ]
    }
    }
    Copy
    Note
    In case of leaving the SET/ADD/REMOVE playload empty, the set operation will be applied. It means that:

    links which are not defined in the new playload will be removed
    existing links will stay the same
    new links will be added.

    - GET ​/api​/test-plan​/{testKey} : Get test plan
        Responses
        Success
        Example Value
        Schema
        {
        "projectKey": "KEY-1",
        "summary": "Example of a summary.",
        "description": "Example of a description.",
        "assigneeId": "12345678901234",
        "parentTestKey": "KEY-1",
        "testKey": "KEY-1",
        "priority": {
            "id": 10000,
            "name": "High"
        },
        "status": {
            "id": 123,
            "statusName": "name"
        },
        "labels": [
            "label1",
            "label2",
            "label3"
        ],
        "components": [
            {
            "id": 1
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "versions": [
            {
            "id": "1"
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "timeEstimate": "5h 30m",
        "environment": "Chrome",
        "executions": [
            {
            "testKey": "KEY-1",
            "issueId": 123
            }
        ],
        "includedTestCases": [
            {
            "testKey": "KEY-1",
            "issueId": 123
            }
        ],
        "allFields": {
            "additionalProp1": {},
            "additionalProp2": {},
            "additionalProp3": {}
        }
        }


    - PUT ​/api​/test-plan​/{testKey} : Update test plan
        Request body
        application/json
        Example Value
        Schema
        {
        "summary": "Example of a summary.",
        "description": "Example of a description.",
        "assigneeId": "12345678901234",
        "parentTestKey": "KEY-1",
        "testKey": "KEY-1",
        "priority": {
            "id": 10000,
            "name": "High"
        },
        "labels": [
            "label1",
            "label2",
            "label3"
        ],
        "components": [
            {
            "id": 1
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "versions": [
            {
            "id": "1"
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "timeEstimate": "5h 30m",
        "executeTransition": {
            "id": 123,
            "name": "name"
        },
        "environment": "Chrome",
        "includedTestCases": [
            {
            "testKey": "KEY-1",
            "issueId": 123
            }
        ]
        }


    - DELETE ​/api​/test-plan​/{testKey} : Delete test plan.
    - PUT ​/api​/test-plan​/{testKey}​/tc-order : Update test plan test case order
        Request body
        application/json
        Example Value
        Schema
        {
        "testCaseOrder": [
            1,
            2,
            3
        ]
        }

    - POST ​/api​/test-plan : Create test plan
        Request body
        Example Value
        Schema
        {
        "projectKey": "KEY-1",
        "summary": "Example of a summary.",
        "description": "Example of a description.",
        "assigneeId": "12345678901234",
        "parentTestKey": "KEY-1",
        "testKey": "KEY-1",
        "priority": {
            "id": 10000,
            "name": "High"
        },
        "status": {
            "id": 123,
            "statusName": "name"
        },
        "labels": [
            "label1",
            "label2",
            "label3"
        ],
        "components": [
            {
            "id": 1
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "versions": [
            {
            "id": "1"
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "timeEstimate": "5h 30m",
        "environment": "Chrome",
        "executions": [
            {
            "testKey": "KEY-1",
            "issueId": 123
            }
        ],
        "includedTestCases": [
            {
            "testKey": "KEY-1",
            "issueId": 123
            }
        ]
        }

        Responses
        Success
        Example Value
        Schema
        {
        "issueId": 10001,
        "issueKey": "TES-1",
        "testKey": "TES-1",
        "summary": "Example of a summary.",
        "self": "string",
        "warnings": [
            "string"
        ]
        }


5. Test Execution
    Test Execution
    Test Execution is the process of executing Test Plans and monitoring particular Test Case Executions results. Test Execution has the same structure as Test Plan. It consists of a Test Cases list, where everyone can monitor the current status of each Test Case Execution. It’s also possible to assign Test Executions to a concrete person.

    Note
    While referring to a Test Case, Test Plan and Test Execution, make sure you properly defined their names:
    TEST_CASES
    TEST_PLANS
    TEST_EXECUTIONS

    V1 API
    Note
    Starting from RTM 6.0 version, we recommend you to use V2 API. We still support V1 API in older RTM releases.

    - GET ​/api​/test-execution​/{testKey} : Get test execution
        Request body
        Example Value
        Schema
        {
        "summary": "Example of a summary.",
        "description": "Example of a description.",
        "assigneeId": "12345678901234",
        "parentTestKey": "KEY-1",
        "testKey": "KEY-1",
        "priority": {
            "id": 10000,
            "name": "High"
        },
        "labels": [
            "label1",
            "label2",
            "label3"
        ],
        "components": [
            {
            "id": 1
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "versions": [
            {
            "id": "1"
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "timeEstimate": "5h 30m",
        "executeTransition": {
            "id": 123,
            "name": "name"
        },
        "environment": "Chrome",
        "result": {
            "statusId": 0,
            "statusName": "string",
            "name": "string"
        }
        }

    - PUT ​/api​/test-execution​/{testKey} : Update test execution
        Request body
        Example Value
        Schema
        {
        "summary": "Example of a summary.",
        "description": "Example of a description.",
        "assigneeId": "12345678901234",
        "parentTestKey": "KEY-1",
        "testKey": "KEY-1",
        "priority": {
            "id": 10000,
            "name": "High"
        },
        "labels": [
            "label1",
            "label2",
            "label3"
        ],
        "components": [
            {
            "id": 1
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "versions": [
            {
            "id": "1"
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "timeEstimate": "5h 30m",
        "executeTransition": {
            "id": 123,
            "name": "name"
        },
        "environment": "Chrome",
        "result": {
            "statusId": 0,
            "statusName": "string",
            "name": "string"
        }
        }

    - DELETE ​/api​/test-execution​/{testKey} : Delete test execution
    - POST ​/api​/test-execution​/execute​/{testPlanTestKey} : Create test execution
        Request body
        Example Value
        Schema
        {
        "testCaseIssueKeys": "TES-1",
        "testKey": "TES-1",
        "description": "Description field value",
        "assigneeId": "12345678901234",
        "environment": "Chrome",
        "parentTestKey": "TES-1",
        "startDate": "2020-12-23",
        "endDate": "2020-12-24",
        "versions": [
            "1.1",
            "1.2"
        ],
        "labels": [
            "Frontend",
            "Login"
        ],
        "components": [
            "Component 1",
            "Component 2"
        ]
        }
        Responses
        Success
        Example Value
        Schema
        {
        "issueId": 10001,
        "issueKey": "TES-1",
        "testKey": "TES-1",
        "summary": "Example of a summary.",
        "self": "string",
        "warnings": [
            "string"
        ]
        }

    - GET ​/api​/test-execution​/status​/{testKey} : Get test execution status
        Responses
        Success
        Example Value
        Schema
        {
        "executionStatus": "Pending",
        "executionResult": "Unknown",
        "failureReason": "Overloaded tenant",
        "failureMessage": "Failure message"
        }


6. Test Case Execution
    Test Case Execution
    Test Case Execution is a status and description of a particular Test Case’s progress. At this stage, the team members can test, add comments, attachment, and change the results of each Test Case. Test Case Executions are created as testing objects inside the Test Execution step.

    Info
    To keep our REST API simple and semantically correct, we plan to add small changes in removing defects, both from Test Case Executions and Test Case Execution Steps. Since 29th February 2022, Defect Test Key should be provided in path - not in request body.

    Following endpoints will be affected by our changes:

    DELETE /api/test-case-execution/{testKey}/defect → 
    DELETE /api/test-case-execution/{testKey}/defect/{defectTestKey}
    DELETE /api/v2/test-case-execution/{testKey}/defect → 
    DELETE /api/v2/test-case-execution/{testKey}/defect/{defectTestKey}
    DELETE /api/v2/test-case-execution/{testKey}/step/{stepId}/defect →
    DELETE /api/v2/test-case-execution/{testKey}/step/{stepId}/defect/{defectTestKey} 
    As you may notice, since 29th February 2022 all endpoints will require {defectTestKey} in the path. It will not require any request body.

    V1 API
    Note
    We recommend you to use V2 instead of V1 API. We’re going to stop supporting V1 in the future.

    - GET  ​/api​/test-case-execution​/{testKey} : Get the test case using the test key.
        Responses
        Success
        Example Value
        Schema
        {
        "id": 12345,
        "summary": "Example of a summary.",
        "preconditions": "Check your project configuration before the test.",
        "executionGroups": [
            {
            "id": 123,
            "name": "name",
            "ordinal": 1,
            "linkedFrom": 123,
            "executionSteps": [
                {
                "id": 123,
                "ordinal": 1,
                "step": {
                    "id": 123,
                    "ordinal": 1,
                    "stepColumns": [
                    {
                        "id": 123,
                        "columnId": 1,
                        "ordinal": 1,
                        "value": "Example value",
                        "name": "Actions"
                    }
                    ],
                    "stepAttachments": [
                    {
                        "attachmentId": 123,
                        "attachmentMetadataUrl": "https://example.com"
                    }
                    ]
                },
                "currentStatus": {
                    "id": 123,
                    "name": "name",
                    "color": "#FFFFFF",
                    "finalStatus": true,
                    "statusName": "name"
                },
                "evidences": [
                    {
                    "id": 123,
                    "attachmentId": 12345678,
                    "attachmentMetadataUrl": "https://example.com"
                    }
                ],
                "executionDefects": [
                    {
                    "id": 123,
                    "issueId": 123
                    }
                ]
                }
            ]
            }
        ],
        "executionDate": "2023-06-28T08:24:10.992Z",
        "creationDate": "2023-06-28T08:24:10.992Z",
        "updatedDate": "2023-06-28T08:24:10.992Z",
        "attachmentIds": [
            0
        ],
        "testKey": "TES-1",
        "actualTime": 0,
        "assigneeId": "1234567891234",
        "environment": "Chrome",
        "result": {
            "id": 123,
            "name": "name",
            "color": "#FFFFFF",
            "finalStatus": true,
            "statusName": "name"
        },
        "priority": {
            "id": 10000,
            "name": "High"
        }
        }


    - PUT ​/api​/test-case-execution​/{testKey} : Update test case execution
        Request body
        Example Value
        Schema
        {
        "testKey": "TES-1",
        "actualTime": 123,
        "assigneeId": "1234567891234",
        "environment": "Chrome",
        "result": {
            "id": 123,
            "name": "name",
            "color": "#FFFFFF",
            "finalStatus": true,
            "statusName": "name"
        },
        "priority": {
            "id": 10000,
            "name": "High"
        }
        }

    - PUT ​/api​/test-case-execution​/{testKey}​/step​/{stepIndex} : Update step status
        Request body
        Example Value
        Schema
        {
        "id": 1,
        "name": "To do",
        "statusName": "string"
        }
    
        Responses
        Example Value
        Schema
        {
        "errorMessages": [
            "error 1",
            "error 2",
            "error 3"
        ],
        "error": "string",
        "errors": {
            "additionalProp1": "string",
            "additionalProp2": "string",
            "additionalProp3": "string"
        },
        "error_description": "Error description"
        }

    - PUT ​/api​/test-case-execution​/{testKey}​/step​/{stepIndex}​/status : Update step status
        Request body
        Example Value
        Schema
        {
        "id": 1,
        "name": "To do",
        "statusName": "string"
        }

    - PUT ​/api​/test-case-execution​/{testKey}​/step​/{stepIndex}​/comment : Update step comment
        Request body
        Example Value
        Schema
        {
        "text": "Example of a comment"
        }

    - DELETE ​/api​/test-case-execution​/{testKey}​/step​/{stepIndex}​/comment : Delete step comment
    - PUT ​/api​/test-case-execution​/{testKey}​/defect : Link defect to the test case execution
        Request body
        Example Value
        Schema
        {
        "testKey": "KEY-1",
        "issueId": 123
        }

    - GET ​/api​/test-case-execution​/test-case​/{testKey} : Get all test case executions related to Test Case identified by the provided test key.
        Responses
        Success
        Example Value
        Schema
        {
        "id": 12345,
        "summary": "Example of a summary.",
        "preconditions": "Check your project configuration before the test.",
        "executionGroups": [
            {
            "id": 123,
            "name": "name",
            "ordinal": 1,
            "linkedFrom": 123,
            "executionSteps": [
                {
                "id": 123,
                "ordinal": 1,
                "step": {
                    "id": 123,
                    "ordinal": 1,
                    "stepColumns": [
                    {
                        "id": 123,
                        "columnId": 1,
                        "ordinal": 1,
                        "value": "Example value",
                        "name": "Actions"
                    }
                    ],
                    "stepAttachments": [
                    {
                        "attachmentId": 123,
                        "attachmentMetadataUrl": "https://example.com"
                    }
                    ]
                },
                "currentStatus": {
                    "id": 123,
                    "name": "name",
                    "color": "#FFFFFF",
                    "finalStatus": true,
                    "statusName": "name"
                },
                "evidences": [
                    {
                    "id": 123,
                    "attachmentId": 12345678,
                    "attachmentMetadataUrl": "https://example.com"
                    }
                ],
                "executionDefects": [
                    {
                    "id": 123,
                    "issueId": 123
                    }
                ]
                }
            ]
            }
        ],
        "executionDate": "2023-06-28T08:24:10.992Z",
        "creationDate": "2023-06-28T08:24:10.992Z",
        "updatedDate": "2023-06-28T08:24:10.992Z",
        "attachmentIds": [
            0
        ],
        "testKey": "TES-1",
        "actualTime": 0,
        "assigneeId": "1234567891234",
        "environment": "Chrome",
        "result": {
            "id": 123,
            "name": "name",
            "color": "#FFFFFF",
            "finalStatus": true,
            "statusName": "name"
        },
        "priority": {
            "id": 10000,
            "name": "High"
        }
        }

    - DELETE ​/api​/test-case-execution​/{testKey}​/defect​/{defectTestKey} : Remove defect from the test case execution.
    - DELETE ​/api​/test-case-execution​/{testKey}​/attachment​/{attachmentId} : Delete attachment from the test case execution identified by the given test key.

    - PUT ​/api​/test-case-execution-comment​/{testKey}​/comments : Get comments using test case execution test key.
        Example Value
        Schema
        {
        "text": "Example of a comment"
        }
        Responses
        Code	
        Example Value
        Schema
        {
        "errorMessages": [
            "error 1",
            "error 2",
            "error 3"
        ],
        "error": "string",
        "errors": {
            "additionalProp1": "string",
            "additionalProp2": "string",
            "additionalProp3": "string"
        },
        "error_description": "Error description"
        }


    - POST ​/api​/test-case-execution-comment​/{testKey}​/comments : Add comment to the test case execution.
        Request body
        application/json
        Example Value
        Schema
        {
        "text": "Example of comment"
        }

        Responses
        Success
        Example Value
        Schema
        {
        "id": 1,
        "testCaseExecutionId": 100,
        "atlassianHostKey": "7f337526-6e7a-3b39-b33e-4d9fd891bbf9",
        "accountId": "1234567891234",
        "text": "Example of comment",
        "creationDate": "2025-12-05T17:51:48.690Z",
        "updatedDate": "2025-12-05T17:51:48.690Z"
        }


    - PUT ​/api​/test-case-execution-comment​/comments​/{id} : Update test case execution comment.
        Request body
        application/json
        Example Value
        Schema
        {
        "text": "Example of comment"
        }
        Responses
        Code	Description
        204
        Success

        Media type

        application/json
        Controls Accept header.
        Example Value
        Schema
        {
        "id": 1,
        "testCaseExecutionId": 100,
        "atlassianHostKey": "7f337526-6e7a-3b39-b33e-4d9fd891bbf9",
        "accountId": "1234567891234",
        "text": "Example of comment",
        "creationDate": "2025-12-05T17:51:06.975Z",
        "updatedDate": "2025-12-05T17:51:06.975Z"
        }

    - DELETE ​/api​/test-case-execution-comment​/comments​/{id} : Delete test case execution comment


7. Defects
    Defect can be defined as an error or bug that appears during the Test Execution. As a result of finding such bugs in Test Case Execution, a tester creates a defect. Defects are related to the whole Test Case and Test Execution.

    How to set up links
    Operation SET - generates an exact set of links indicated in the payload

    {
    "identifyingTestCases": {
        "set": [
        {
            "testKey": "{{TcTestKey2}}"
        }
        ]
    }
    }
    Copy
    Operation ADD - adds links indicated in the payload

    {
    "identifyingTestCases": {
        "add": [
        {
            "testKey": "{{TcTestKey2}}"
        }
        ]
    }
    }
    Copy
    Operation REMOVE - deletes links indicated in the payload

    {
    "identifyingTestCases": {
        "remove": [
        {
            "testKey": "{{TcTestKey2}}"
        }
        ]
    }
    }
    Copy

    Note
    In case of leaving the SET/ADD/REMOVE playload empty, the set operation will be applied. It means that:

    links which are not defined in the new playload will be removed
    existing links will stay the same
    new links will be added.

    - GET ​/api​/defect​/{testKey} : Get defect
        Responses
        Success
        Example Value
        Schema
        {
        "issueTypeId": 123,
        "detectingExecutions": [
            {
            "testKey": "KEY-1",
            "issueId": 123
            }
        ],
        "projectKey": "KEY-1",
        "summary": "Example of a summary.",
        "description": "Example of a description.",
        "assigneeId": "12345678901234",
        "parentTestKey": "KEY-1",
        "testKey": "KEY-1",
        "priority": {
            "id": 10000,
            "name": "High"
        },
        "status": {
            "id": 123,
            "statusName": "name"
        },
        "labels": [
            "label1",
            "label2",
            "label3"
        ],
        "components": [
            {
            "id": 1
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "versions": [
            {
            "id": "1"
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "timeEstimate": "5h 30m",
        "environment": "Chrome",
        "identifyingTestCases": [
            {
            "testKey": "KEY-1",
            "issueId": 123
            }
        ],
        "allFields": {
            "additionalProp1": {},
            "additionalProp2": {},
            "additionalProp3": {}
        }
        }

    - PUT ​/api​/defect​/{testKey} : Update defect
        Request body
        Example Value
        Schema
        {
        "issueTypeId": 123,
        "detectingExecutions": [
            {
            "testKey": "KEY-1",
            "issueId": 123
            }
        ],
        "summary": "Example of a summary.",
        "description": "Example of a description.",
        "assigneeId": "12345678901234",
        "parentTestKey": "KEY-1",
        "testKey": "KEY-1",
        "priority": {
            "id": 10000,
            "name": "High"
        },
        "labels": [
            "label1",
            "label2",
            "label3"
        ],
        "components": [
            {
            "id": 1
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "versions": [
            {
            "id": "1"
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "timeEstimate": "5h 30m",
        "executeTransition": {
            "id": 123,
            "name": "name"
        },
        "environment": "Chrome",
        "identifyingTestCases": [
            {
            "testKey": "KEY-1",
            "issueId": 123
            }
        ]
        }

    - DELETE ​/api​/defect​/{testKey} : Delete defect.
    - POST ​/api​/defect : Create defect
        Request body
        Example Value
        Schema
        {
        "issueTypeId": 123,
        "detectingExecutions": [
            {
            "testKey": "KEY-1",
            "issueId": 123
            }
        ],
        "projectKey": "KEY-1",
        "summary": "Example of a summary.",
        "description": "Example of a description.",
        "assigneeId": "12345678901234",
        "parentTestKey": "KEY-1",
        "testKey": "KEY-1",
        "priority": {
            "id": 10000,
            "name": "High"
        },
        "status": {
            "id": 123,
            "statusName": "name"
        },
        "labels": [
            "label1",
            "label2",
            "label3"
        ],
        "components": [
            {
            "id": 1
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "versions": [
            {
            "id": "1"
            },
            {
            "id": "2"
            },
            {
            "id": "3"
            }
        ],
        "timeEstimate": "5h 30m",
        "environment": "Chrome",
        "identifyingTestCases": [
            {
            "testKey": "KEY-1",
            "issueId": 123
            }
        ]
        }

        Responses
        Success
        Example Value
        Schema
        {
        "issueId": 10001,
        "issueKey": "TES-1",
        "testKey": "TES-1",
        "summary": "Example of a summary.",
        "self": "string",
        "warnings": [
            "string"
        ]
        } 


8. Tree Structure
Tree structure
Each module has its own tree view which can be modified in any way. It’s possible to create new folders and sub-folders, as well as testing objects, and also change their place inside the structure.

- PUT ​/api​/v2​/tree​/import : Import jira issue to RTM tree
    Request body
    Example Value
    Schema
    {
    "testKey": "TES-1",
    "issueKey": "TES-2",
    "issueId": 123
    }

- PUT ​/api​/tree​/{testKey}​/node : Move tree node
    Request body
    Example Value
    Schema
    {
    "testKey": "KEY-1"
    }

- DELETE ​/api​/tree​/{testKey}​/node : Delete node.
- GET ​/api​/tree​/{testKey}​/folder : Get folder
    Responses
    Success
    Example Value
    Schema
    {
    "testKey": "TES-1",
    "folderName": "Folder name"
    }

- PUT ​/api​/tree​/{testKey}​/folder : Update folder.
    Request body
    Example Value
    Schema
    {
    "testKey": "KEY-1",
    "folderName": "folder1"
    }


- PUT ​/api​/tree​/import : Import jira issue to RTM tree
    Request body
    Example Value
    Schema
    {
    "testKey": "KEY-1",
    "issueId": 123
    }

- POST ​/api​/tree​/{projectId}​/folder : Create folder
    Request body
    Example Value
    Schema
    {
    "parentTestKey": "TES-1",
    "testKey": "TES-2",
    "folderName": "Folder name",
    "treeType": "REQUIREMENTS"
    }

- GET ​/api​/v2​/tree​/{projectId}​/{treeType} : Get tree structure
    Responses
    200
    Example Value
    Schema
    {
    "id": 12345,
    "testKey": "TES-1",
    "issueId": 123,
    "folderName": "Folder name",
    "children": [
        {
        "testKey": "TES-1",
        "children": [
            null
        ]
        }
    ]
    }

- DELETE ​/api​/v2​/tree​/{projectId}​/{treeType} : Clearing tree structure
- GET ​/api​/tree​/{projectId}​/{treeType} : Get tree structure
    Responses
    Success!
    Example Value
    Schema
    {
    "testKey": "TES-1",
    "children": [
        null
    ]
    }