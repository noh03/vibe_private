https://docs.atlassian.com/software/jira/docs/api/REST/9.12.0/

Atlassian Developers
Jira Server platform REST API reference
Jira 9.12.0

Welcome to the Jira Server platform REST API reference. You can use this REST API to build apps for Jira, develop integrations between Jira and other applications, or script interactions with Jira. This page documents the REST resources available in Jira Server platform, along with expected HTTP response codes and sample requests.

Looking for the REST API reference for a different Jira version? Follow the links below.

Jira Cloud platform REST API
List of all Jira REST APIs
Getting started
If you haven't integrated with Jira Server before, read the Getting started guide in the Jira Server developer documentation. You may also want to read our Jira REST API overview, which describes how the Jira REST APIs work, including a simple example of a REST call.

Authentication
The preferred authentication methods for the Jira REST APIs are OAuth and HTTP basic authentication (when using SSL).

Jira itself uses cookie-based authentication in the browser, so you can call REST from JavaScript on the page and rely on the authentication that the browser has established. To reproduce the behavior of the Jira log-in page (for example, to display authentication error messages to users) can POST to the /auth/1/session resource.

URI Structure
Jira's REST APIs provide access to resources (data entities) via URI paths. To use a REST API, your application will make an HTTP request and parse the response. The Jira REST API uses JSON as its communication format, and the standard HTTP methods like GET, PUT, POST and DELETE (see API descriptions below for which methods are available for each resource). URIs for Jira's REST API resource have the following structure:

http://host:port/context/rest/api-name/api-version/resource-name
Currently there are two API names available, which will be discussed further below:

auth - for authentication-related operations, and
api - for everything else.
The current API version is 2. However, there is also a symbolic version, called latest, which resolves to the latest version supported by the given Jira instance. As an example, if you wanted to retrieve the JSON representation of issue JRA-9 from Atlassian's public issue tracker, you would access:

https://jira.atlassian.com/rest/api/latest/issue/JRA-9
There is a WADL document that contains the documentation for each resource in the Jira REST API. It is available here.

Expansion
In order to simplify API responses, the Jira REST API uses resource expansion. This means the API will only return parts of the resource when explicitly requested.

You can use the expand query parameter to specify a comma-separated list of entities that you want expanded, identifying each of them by name. For example, appending ?expand=names,renderedFields to an issue's URI requests the inclusion of the translated field names and the HTML-rendered field values in the response. Continuing with our example above, we would use the following URL to get that information for JRA-9:

https://jira.atlassian.com/rest/api/latest/issue/JRA-9?expand=names,renderedFields
To discover the identifiers for each entity, look at the expand property in the parent object. In the JSON example below, the resource declares widgets as being expandable.

{
    "expand": "widgets",
    "self": "http://www.example.com/jira/rest/api/resource/KEY-1",
    "widgets": {
        "widgets": [],
        "size": 5
    }
}
You can use the dot notation to specify expansion of entities within another entity. For example ?expand=widgets.fringels would expand the widgets collection and also the fringel property on each widget.

Pagination
Jira uses pagination to limit the response size for resources that return a potentially large collection of items. A request to a paged API will result in a values array wrapped in a JSON object with some paging metadata, for example:

    {
        "startAt" : 0,
        "maxResults" : 10,
        "total": 200,
        "values": [
            { /* result 0 */ },
            { /* result 1 */ },
            { /* result 2 */ }
        ]
    }
Clients can use the "startAt" and "maxResults" parameters to retrieve the desired numbers of results.

The "maxResults" parameter indicates how many results to return per page. Each API may have a different limit for number of items returned.

The "startAt" parameter indicates which item should be used as the first item in the page of results.

Important: The response contains a "total" field which denotes the total number of entities contained in all pages. This number may change as the client requests the subsequent pages. A client should always assume that the requested page can be empty. REST API consumers should also consider the field to be optional. In cases, when calculating this value is too expensive we may not include this in response.

Ordering
Some resources support ordering by a specific field. Ordering request is provided in the orderBy query parameter. See the docs for specific methods to see which fields they support and if they support ordering at all.

Ordering can be ascending or descending. By default it's ascending. To specify the ordering use "-" or "+" sign. Examples:

?orderBy=name
Order by "name" ascending
?orderBy=+name
Order by "name" ascending
?orderBy=-name
Order by "name" descending
Experimental methods
Methods marked as experimental may change without an earlier notice. We are looking for your feedback for these methods.

Special request and response headers
X-AUSERNAME - Response header which contains either username of the authenticated user or 'anonymous'.
X-Atlassian-Token - methods which accept multipart/form-data will only process requests with 'X-Atlassian-Token: no-check' header.
Error responses
Most resources will return a response body in addition to the status code. Usually, the JSON schema of the entity returned is the following:
{
    "id": "https://docs.atlassian.com/jira/REST/schema/error-collection#",
    "title": "Error Collection",
    "type": "object",
    "properties": {
        "errorMessages": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "errors": {
            "type": "object",
            "patternProperties": {
                ".+": {
                    "type": "string"
                }
            },
            "additionalProperties": false
        },
        "status": {
            "type": "integer"
        }
    },
    "additionalProperties": false
}
ResourcesExpand all methods
api/2Expand all methods
Provide permission information for the current user.

Get permissions
GET /rest/api/2/mypermissions
Get all permissions
GET /rest/api/2/permissions
api/2/application-propertiesExpand all methods
Get property
GET /rest/api/2/application-properties
Set property via restful table
PUT /rest/api/2/application-properties/{id}
Get advanced settings
GET /rest/api/2/application-properties/advanced-settings
api/2/applicationroleExpand all methods
Provides REST access to Jira's Application Roles.

Put bulk
PUT /rest/api/2/applicationrole
Get all
GET /rest/api/2/applicationrole
Get
GET /rest/api/2/applicationrole/{key}
Put
PUT /rest/api/2/applicationrole/{key}
api/2/attachmentExpand all methods
Get attachment
GET /rest/api/2/attachment/{id}
Remove attachment
DELETE /rest/api/2/attachment/{id}
Expand for humans  experimental
GET /rest/api/2/attachment/{id}/expand/human
Expand for machines  experimental
GET /rest/api/2/attachment/{id}/expand/raw
Get attachment meta
GET /rest/api/2/attachment/meta
api/2/auditingExpand all methods
Resource representing the auditing records

Add record  deprecated
POST /rest/api/2/auditing/record
Get records  deprecated
GET /rest/api/2/auditing/record
api/2/avatarExpand all methods
Get all system avatars
GET /rest/api/2/avatar/{type}/system
Store temporary avatar
POST /rest/api/2/avatar/{type}/temporary
Create avatar from temporary
POST /rest/api/2/avatar/{type}/temporaryCrop
api/2/clusterExpand all methods
It gives possibility to manage old node in cluster.

Get all nodes
GET /rest/api/2/cluster/nodes
Request current index from node
PUT /rest/api/2/cluster/index-snapshot/{nodeId}
Delete node
DELETE /rest/api/2/cluster/node/{nodeId}
Change node state to offline
PUT /rest/api/2/cluster/node/{nodeId}/offline
api/2/cluster/zduExpand all methods
Approve upgrade
POST /rest/api/2/cluster/zdu/approve
Cancel upgrade
POST /rest/api/2/cluster/zdu/cancel
Acknowledge errors
POST /rest/api/2/cluster/zdu/retryUpgrade
Set ready to upgrade
POST /rest/api/2/cluster/zdu/start
Get state
GET /rest/api/2/cluster/zdu/state
api/2/comment/{commentId}/propertiesExpand all methods
Get properties keys  experimental
GET /rest/api/2/comment/{commentId}/properties
Delete property  experimental
DELETE /rest/api/2/comment/{commentId}/properties/{propertyKey}
Set property  experimental
PUT /rest/api/2/comment/{commentId}/properties/{propertyKey}
Get property  experimental
GET /rest/api/2/comment/{commentId}/properties/{propertyKey}
api/2/componentExpand all methods
Create component
POST /rest/api/2/component
Update component
PUT /rest/api/2/component/{id}
Get component
GET /rest/api/2/component/{id}
Delete
DELETE /rest/api/2/component/{id}
Get component related issues
GET /rest/api/2/component/{id}/relatedIssueCounts
Get paginated components  experimental
GET /rest/api/2/component/page
api/2/configurationExpand all methods
Get configuration
GET /rest/api/2/configuration
api/2/customFieldOptionExpand all methods
Get custom field option
GET /rest/api/2/customFieldOption/{id}
api/2/customFieldsExpand all methods
Bulk delete custom fields
DELETE /rest/api/2/customFields
Get custom fields
GET /rest/api/2/customFields
Get custom field options  experimental
GET /rest/api/2/customFields/{customFieldId}/options
api/2/dashboardExpand all methods
List
GET /rest/api/2/dashboard
Get dashboard
GET /rest/api/2/dashboard/{id}
api/2/dashboard/{dashboardId}/items/{itemId}/propertiesExpand all methods
Get properties keys
GET /rest/api/2/dashboard/{dashboardId}/items/{itemId}/properties
Delete property
DELETE /rest/api/2/dashboard/{dashboardId}/items/{itemId}/properties/{propertyKey}
Set property
PUT /rest/api/2/dashboard/{dashboardId}/items/{itemId}/properties/{propertyKey}
Get property
GET /rest/api/2/dashboard/{dashboardId}/items/{itemId}/properties/{propertyKey}
api/2/email-templatesExpand all methods
Upload email templates
POST /rest/api/2/email-templates
Download email templates
GET /rest/api/2/email-templates
Apply email templates
POST /rest/api/2/email-templates/apply
Revert email templates to default
POST /rest/api/2/email-templates/revert
Get email types
GET /rest/api/2/email-templates/types
api/2/fieldExpand all methods
Create custom field
POST /rest/api/2/field
Get fields
GET /rest/api/2/field
api/2/filterExpand all methods
Resource for searches.

Create filter
POST /rest/api/2/filter
Edit filter
PUT /rest/api/2/filter/{id}
Delete filter
DELETE /rest/api/2/filter/{id}
Get filter
GET /rest/api/2/filter/{id}
Default columns
GET /rest/api/2/filter/{id}/columns
Set columns
PUT /rest/api/2/filter/{id}/columns
Reset columns
DELETE /rest/api/2/filter/{id}/columns
Get share permissions
GET /rest/api/2/filter/{id}/permission
Add share permission
POST /rest/api/2/filter/{id}/permission
Get share permission
GET /rest/api/2/filter/{id}/permission/{permissionId}
Delete share permission
DELETE /rest/api/2/filter/{id}/permission/{permission-id}
Get default share scope
GET /rest/api/2/filter/defaultShareScope
Set default share scope
PUT /rest/api/2/filter/defaultShareScope
Get favourite filters
GET /rest/api/2/filter/favourite
api/2/groupExpand all methods
Create group
POST /rest/api/2/group
Get group  deprecated
GET /rest/api/2/group
Remove group
DELETE /rest/api/2/group
Get users from group
GET /rest/api/2/group/member
Add user to group
POST /rest/api/2/group/user
Remove user from group
DELETE /rest/api/2/group/user
api/2/groupsExpand all methods
REST endpoint for searching groups in a group picker

Find groups
GET /rest/api/2/groups/picker
api/2/groupuserpickerExpand all methods
Find users and groups
GET /rest/api/2/groupuserpicker
api/2/index/summaryExpand all methods
REST resource for index summary

Get index summary  experimental
GET /rest/api/2/index/summary
api/2/index-snapshotExpand all methods
REST resource for index snapshot operations.

Create index snapshot
POST /rest/api/2/index-snapshot
List index snapshot
GET /rest/api/2/index-snapshot
Is index snapshot running
GET /rest/api/2/index-snapshot/isRunning
api/2/issueExpand all methods
Create issue
POST /rest/api/2/issue
Create issues
POST /rest/api/2/issue/bulk
Get issue
GET /rest/api/2/issue/{issueIdOrKey}
Delete issue
DELETE /rest/api/2/issue/{issueIdOrKey}
Edit issue
PUT /rest/api/2/issue/{issueIdOrKey}
Archive issue
PUT /rest/api/2/issue/{issueIdOrKey}/archive
Assign
PUT /rest/api/2/issue/{issueIdOrKey}/assignee
Get comments
GET /rest/api/2/issue/{issueIdOrKey}/comment
Add comment
POST /rest/api/2/issue/{issueIdOrKey}/comment
Update comment
PUT /rest/api/2/issue/{issueIdOrKey}/comment/{id}
Delete comment
DELETE /rest/api/2/issue/{issueIdOrKey}/comment/{id}
Get comment
GET /rest/api/2/issue/{issueIdOrKey}/comment/{id}
Set pin comment
PUT /rest/api/2/issue/{issueIdOrKey}/comment/{id}/pin
Get edit issue meta
GET /rest/api/2/issue/{issueIdOrKey}/editmeta
Notify
POST /rest/api/2/issue/{issueIdOrKey}/notify
Get pinned comments
GET /rest/api/2/issue/{issueIdOrKey}/pinned-comments
Get remote issue links
GET /rest/api/2/issue/{issueIdOrKey}/remotelink
Create or update remote issue link
POST /rest/api/2/issue/{issueIdOrKey}/remotelink
Delete remote issue link by global id
DELETE /rest/api/2/issue/{issueIdOrKey}/remotelink
Get remote issue link by id
GET /rest/api/2/issue/{issueIdOrKey}/remotelink/{linkId}
Update remote issue link
PUT /rest/api/2/issue/{issueIdOrKey}/remotelink/{linkId}
Delete remote issue link by id
DELETE /rest/api/2/issue/{issueIdOrKey}/remotelink/{linkId}
Restore issue
PUT /rest/api/2/issue/{issueIdOrKey}/restore
Get transitions
GET /rest/api/2/issue/{issueIdOrKey}/transitions
Do transition
POST /rest/api/2/issue/{issueIdOrKey}/transitions
Remove vote
DELETE /rest/api/2/issue/{issueIdOrKey}/votes
Add vote
POST /rest/api/2/issue/{issueIdOrKey}/votes
Get votes
GET /rest/api/2/issue/{issueIdOrKey}/votes
Get issue watchers
GET /rest/api/2/issue/{issueIdOrKey}/watchers
Add watcher
POST /rest/api/2/issue/{issueIdOrKey}/watchers
Remove watcher
DELETE /rest/api/2/issue/{issueIdOrKey}/watchers
Get issue worklog
GET /rest/api/2/issue/{issueIdOrKey}/worklog
Add worklog
POST /rest/api/2/issue/{issueIdOrKey}/worklog
Get worklog
GET /rest/api/2/issue/{issueIdOrKey}/worklog/{id}
Update worklog
PUT /rest/api/2/issue/{issueIdOrKey}/worklog/{id}
Delete worklog
DELETE /rest/api/2/issue/{issueIdOrKey}/worklog/{id}
Archive issues
POST /rest/api/2/issue/archive
Get create issue meta project issue types
GET /rest/api/2/issue/createmeta/{projectIdOrKey}/issuetypes
Get create issue meta fields
GET /rest/api/2/issue/createmeta/{projectIdOrKey}/issuetypes/{issueTypeId}
Get issue picker resource
GET /rest/api/2/issue/picker
api/2/issue/{issueIdOrKey}/attachmentsExpand all methods
Issue attachments

Add attachment
POST /rest/api/2/issue/{issueIdOrKey}/attachments
api/2/issue/{issueIdOrKey}/propertiesExpand all methods
Get properties keys  experimental
GET /rest/api/2/issue/{issueIdOrKey}/properties
Delete property  experimental
DELETE /rest/api/2/issue/{issueIdOrKey}/properties/{propertyKey}
Set property  experimental
PUT /rest/api/2/issue/{issueIdOrKey}/properties/{propertyKey}
Get property  experimental
GET /rest/api/2/issue/{issueIdOrKey}/properties/{propertyKey}
api/2/issue/{issueIdOrKey}/subtaskExpand all methods
Get sub tasks
GET /rest/api/2/issue/{issueIdOrKey}/subtask
Can move sub task
GET /rest/api/2/issue/{issueIdOrKey}/subtask/move
Move sub tasks
POST /rest/api/2/issue/{issueIdOrKey}/subtask/move
api/2/issueLinkExpand all methods
The Link Issue Resource provides functionality to manage issue links.

Link issues
POST /rest/api/2/issueLink
Get issue link
GET /rest/api/2/issueLink/{linkId}
Delete issue link
DELETE /rest/api/2/issueLink/{linkId}
api/2/issueLinkTypeExpand all methods
Rest resource to retrieve a list of issue link types.

Get issue link types
GET /rest/api/2/issueLinkType
Create issue link type
POST /rest/api/2/issueLinkType
Get issue link type
GET /rest/api/2/issueLinkType/{issueLinkTypeId}
Delete issue link type
DELETE /rest/api/2/issueLinkType/{issueLinkTypeId}
Update issue link type
PUT /rest/api/2/issueLinkType/{issueLinkTypeId}
api/2/issuesecurityschemesExpand all methods
REST resource that allows to view security schemes defined in the product.

Get issue security schemes
GET /rest/api/2/issuesecurityschemes
Get issue security scheme
GET /rest/api/2/issuesecurityschemes/{id}
api/2/issuetypeExpand all methods
Create issue type
POST /rest/api/2/issuetype
Get issue all types
GET /rest/api/2/issuetype
Get issue type
GET /rest/api/2/issuetype/{id}
Delete issue type
DELETE /rest/api/2/issuetype/{id}
Update issue type
PUT /rest/api/2/issuetype/{id}
Get alternative issue types
GET /rest/api/2/issuetype/{id}/alternatives
Create avatar from temporary
POST /rest/api/2/issuetype/{id}/avatar
Store temporary avatar
POST /rest/api/2/issuetype/{id}/avatar/temporary
Store temporary avatar using multi part
POST /rest/api/2/issuetype/{id}/avatar/temporary
Get paginated issue types  experimental
GET /rest/api/2/issuetype/page
api/2/issuetype/{issueTypeId}/propertiesExpand all methods
This resource allows to store custom properties for issue types.

Get property keys  experimental
GET /rest/api/2/issuetype/{issueTypeId}/properties
Delete property  experimental
DELETE /rest/api/2/issuetype/{issueTypeId}/properties/{propertyKey}
Set property  experimental
PUT /rest/api/2/issuetype/{issueTypeId}/properties/{propertyKey}
Get property  experimental
GET /rest/api/2/issuetype/{issueTypeId}/properties/{propertyKey}
api/2/issuetypeschemeExpand all methods
Resource for managing issue type schemes and their project associations.
An issue type scheme is a named, ordered collection of issue types that is associated with 0..n projects. The contents of the associated issue type scheme determine which issue types are available to a project.

As is the case with {@link IssueTypeResource#deleteIssueType(String, String) issue type deletion}, certain changes to an issue type scheme require issue migrations on the part of affected projects. This resource does not support such migrations, and users are encouraged to use the GUI to perform them when necessary.

Show more
Create issue type scheme
POST /rest/api/2/issuetypescheme
Get all issue type schemes
GET /rest/api/2/issuetypescheme
Get issue type scheme
GET /rest/api/2/issuetypescheme/{schemeId}
Update issue type scheme
PUT /rest/api/2/issuetypescheme/{schemeId}
Delete issue type scheme
DELETE /rest/api/2/issuetypescheme/{schemeId}
Add project associations to scheme
POST /rest/api/2/issuetypescheme/{schemeId}/associations
Get associated projects
GET /rest/api/2/issuetypescheme/{schemeId}/associations
Set project associations for scheme
PUT /rest/api/2/issuetypescheme/{schemeId}/associations
Remove all project associations
DELETE /rest/api/2/issuetypescheme/{schemeId}/associations
Remove project association
DELETE /rest/api/2/issuetypescheme/{schemeId}/associations/{projIdOrKey}
api/2/jql/autocompletedataExpand all methods
Resource for auto complete data for searches.

Get auto complete
GET /rest/api/2/jql/autocompletedata
Get field auto complete for query string
GET /rest/api/2/jql/autocompletedata/suggestions
api/2/licenseValidatorExpand all methods
A REST endpoint to provide simple validation services for a Jira license. Typically used by the setup phase of the Jira application. This will return an object with a list of errors as key, value pairs.Show more
Validate
POST /rest/api/2/licenseValidator
api/2/monitoring/appExpand all methods
Describes endpoint for controlling the App Monitoring feature

Set app monitoring enabled
POST /rest/api/2/monitoring/app
Is app monitoring enabled
GET /rest/api/2/monitoring/app
api/2/monitoring/ipdExpand all methods
Describes endpoint for controlling the IPD Monitoring feature

Is ipd monitoring enabled
GET /rest/api/2/monitoring/ipd
Set app monitoring enabled
POST /rest/api/2/monitoring/ipd
api/2/monitoring/jmxExpand all methods
Are metrics exposed
GET /rest/api/2/monitoring/jmx/areMetricsExposed
Get available metrics
GET /rest/api/2/monitoring/jmx/getAvailableMetrics
Start
POST /rest/api/2/monitoring/jmx/startExposing
Stop
POST /rest/api/2/monitoring/jmx/stopExposing
api/2/mypreferencesExpand all methods
Provide preferences of the currently logged in user.

Set preference
PUT /rest/api/2/mypreferences
Remove preference
DELETE /rest/api/2/mypreferences
Get preference
GET /rest/api/2/mypreferences
api/2/myselfExpand all methods
Currently logged user resource

Update user
PUT /rest/api/2/myself
Get user
GET /rest/api/2/myself
Change my password
PUT /rest/api/2/myself/password
api/2/notificationschemeExpand all methods
Get notification schemes
GET /rest/api/2/notificationscheme
Get notification scheme
GET /rest/api/2/notificationscheme/{id}
api/2/passwordExpand all methods
REST resource for operations related to passwords and the password policy.

Get password policy
GET /rest/api/2/password/policy
Policy check create user
POST /rest/api/2/password/policy/createUser
Policy check update user
POST /rest/api/2/password/policy/updateUser
api/2/permissionschemeExpand all methods
Resource for managing permission schemes and their attributes.
Permission scheme is a collection of permission grants. Each grant holds information about a permission granted to a group of users. These groups of users are called holders and are defined by two values: type and parameter. Type can be for example "group", or "user" and parameter is an additional specification. In case of groups the parameter will hold the group name, and in case of users: user id.

Types can be extended by plugins, but here is a list of all built-in types (expected parameter contents are given in parenthesis):

anyone
Grant for anonymous users.
group (group name)
Grant for the specified group
user (user id)
Grant for the specified user
projectRole (project role id)
Grant for the specified project role
reporter
Grant for an issue reported
projectLead
Grant for a project lead
assignee
Grant for a user assigned to an issue
userCustomField (custom field id)
Grant for a user selected in the specified custom field
groupCustomField (custom field id)
Grant for a user selected in the specified custom field
There are also two "hidden" holder types, which are not available in on-demand but can be used in enterprise instances:

reporterWithCreatePermission
This type can be used only with BROWSE_PROJECTS permission to show only projects where the user has create permission and issues within that where they are the reporter.
assigneeWithAssignablePermission
This type can be used only with BROWSE_PROJECTS permission to show only projects where the user has the assignable permission and issues within that where they are the assignee.
In addition to specifying the permission holder, a permission must be selected. That way a pair of (holder, permission) is created and it represents a single permission grant.

Custom permissions can be added by plugins, but below we present a set of built-in Jira permissions.

ADMINISTER_PROJECTS
BROWSE_PROJECTS
VIEW_DEV_TOOLS
VIEW_READONLY_WORKFLOW
CREATE_ISSUES
EDIT_ISSUES
TRANSITION_ISSUES
SCHEDULE_ISSUES
MOVE_ISSUES
ASSIGN_ISSUES
ASSIGNABLE_USER
RESOLVE_ISSUES
CLOSE_ISSUES
MODIFY_REPORTER
DELETE_ISSUES
LINK_ISSUES
SET_ISSUE_SECURITY
VIEW_VOTERS_AND_WATCHERS
MANAGE_WATCHERS
ADD_COMMENTS
EDIT_ALL_COMMENTS
EDIT_OWN_COMMENTS
DELETE_ALL_COMMENTS
DELETE_OWN_COMMENTS
CREATE_ATTACHMENTS
DELETE_ALL_ATTACHMENTS
DELETE_OWN_ATTACHMENTS
WORK_ON_ISSUES
EDIT_OWN_WORKLOGS
EDIT_ALL_WORKLOGS
DELETE_OWN_WORKLOGS
DELETE_ALL_WORKLOGS
Show more
Get permission schemes
GET /rest/api/2/permissionscheme
Create permission scheme
POST /rest/api/2/permissionscheme
Get scheme attribute  experimental
GET /rest/api/2/permissionscheme/{permissionSchemeId}/attribute/{attributeKey}
Set scheme attribute  experimental
PUT /rest/api/2/permissionscheme/{permissionSchemeId}/attribute/{key}
Get permission scheme
GET /rest/api/2/permissionscheme/{schemeId}
Delete permission scheme
DELETE /rest/api/2/permissionscheme/{schemeId}
Update permission scheme
PUT /rest/api/2/permissionscheme/{schemeId}
Get permission scheme grants
GET /rest/api/2/permissionscheme/{schemeId}/permission
Create permission grant
POST /rest/api/2/permissionscheme/{schemeId}/permission
Delete permission scheme entity
DELETE /rest/api/2/permissionscheme/{schemeId}/permission/{permissionId}
Get permission scheme grant
GET /rest/api/2/permissionscheme/{schemeId}/permission/{permissionId}
api/2/priorityExpand all methods
Get priorities
GET /rest/api/2/priority
Get priority
GET /rest/api/2/priority/{id}
Get priorities
GET /rest/api/2/priority/page
api/2/priorityschemesExpand all methods
Resource for managing priority schemes.

Create priority scheme  experimental
POST /rest/api/2/priorityschemes
Get priority schemes  experimental
GET /rest/api/2/priorityschemes
Delete priority scheme  experimental
DELETE /rest/api/2/priorityschemes/{schemeId}
Update priority scheme  experimental
PUT /rest/api/2/priorityschemes/{schemeId}
Get priority scheme  experimental
GET /rest/api/2/priorityschemes/{schemeId}
api/2/projectExpand all methods
Get all projects
GET /rest/api/2/project
Create project
POST /rest/api/2/project
Update project
PUT /rest/api/2/project/{projectIdOrKey}
Delete project
DELETE /rest/api/2/project/{projectIdOrKey}
Get project
GET /rest/api/2/project/{projectIdOrKey}
Archive project
PUT /rest/api/2/project/{projectIdOrKey}/archive
Create avatar from temporary
POST /rest/api/2/project/{projectIdOrKey}/avatar
Update project avatar
PUT /rest/api/2/project/{projectIdOrKey}/avatar
Delete avatar
DELETE /rest/api/2/project/{projectIdOrKey}/avatar/{id}
Store temporary avatar
POST /rest/api/2/project/{projectIdOrKey}/avatar/temporary
Store temporary avatar using multi part
POST /rest/api/2/project/{projectIdOrKey}/avatar/temporary
Get all avatars
GET /rest/api/2/project/{projectIdOrKey}/avatars
Get project components
GET /rest/api/2/project/{projectIdOrKey}/components
Restore project
PUT /rest/api/2/project/{projectIdOrKey}/restore
Get all statuses
GET /rest/api/2/project/{projectIdOrKey}/statuses
Update project type
PUT /rest/api/2/project/{projectIdOrKey}/type/{newProjectTypeKey}
Get project versions paginated
GET /rest/api/2/project/{projectIdOrKey}/version
Get project versions
GET /rest/api/2/project/{projectIdOrKey}/versions
api/2/project/{projectIdOrKey}/propertiesExpand all methods
Get properties keys  experimental
GET /rest/api/2/project/{projectIdOrKey}/properties
Delete property  experimental
DELETE /rest/api/2/project/{projectIdOrKey}/properties/{propertyKey}
Set property  experimental
PUT /rest/api/2/project/{projectIdOrKey}/properties/{propertyKey}
Get property  experimental
GET /rest/api/2/project/{projectIdOrKey}/properties/{propertyKey}
api/2/project/{projectIdOrKey}/roleExpand all methods
Get project roles
GET /rest/api/2/project/{projectIdOrKey}/role
Get project role
GET /rest/api/2/project/{projectIdOrKey}/role/{id}
Set actors
PUT /rest/api/2/project/{projectIdOrKey}/role/{id}
Delete actor
DELETE /rest/api/2/project/{projectIdOrKey}/role/{id}
Add actor users
POST /rest/api/2/project/{projectIdOrKey}/role/{id}
api/2/project/{projectKeyOrId}/issuesecuritylevelschemeExpand all methods
Resource for associating permission schemes and projects.

Get issue security scheme
GET /rest/api/2/project/{projectKeyOrId}/issuesecuritylevelscheme
api/2/project/{projectKeyOrId}/notificationschemeExpand all methods
Resource for associating notification schemes and projects.

Get notification scheme
GET /rest/api/2/project/{projectKeyOrId}/notificationscheme
api/2/project/{projectKeyOrId}/permissionschemeExpand all methods
Resource for associating permission schemes and projects.

Assign permission scheme
PUT /rest/api/2/project/{projectKeyOrId}/permissionscheme
Get assigned permission scheme
GET /rest/api/2/project/{projectKeyOrId}/permissionscheme
api/2/project/{projectKeyOrId}/priorityschemeExpand all methods
Resource for associating priority schemes and projects.

Assign priority scheme  experimental
PUT /rest/api/2/project/{projectKeyOrId}/priorityscheme
Get assigned priority scheme  experimental
GET /rest/api/2/project/{projectKeyOrId}/priorityscheme
Unassign priority scheme  experimental
DELETE /rest/api/2/project/{projectKeyOrId}/priorityscheme/{schemeId}
api/2/project/{projectKeyOrId}/securitylevelExpand all methods
Provide security level information of the given project for the current user.

Get security levels for project
GET /rest/api/2/project/{projectKeyOrId}/securitylevel
api/2/project/{projectKeyOrId}/workflowschemeExpand all methods
Get workflow scheme for project
GET /rest/api/2/project/{projectKeyOrId}/workflowscheme
api/2/project/typeExpand all methods
Get all project types
GET /rest/api/2/project/type
Get project type by key
GET /rest/api/2/project/type/{projectTypeKey}
Get accessible project type by key
GET /rest/api/2/project/type/{projectTypeKey}/accessible
api/2/projectCategoryExpand all methods
Create project category
POST /rest/api/2/projectCategory
Get all project categories
GET /rest/api/2/projectCategory
Remove project category
DELETE /rest/api/2/projectCategory/{id}
Update project category
PUT /rest/api/2/projectCategory/{id}
Get project category by id
GET /rest/api/2/projectCategory/{id}
api/2/projects/pickerExpand all methods
Search for projects
GET /rest/api/2/projects/picker
api/2/projectvalidateExpand all methods
Get project
GET /rest/api/2/projectvalidate/key
api/2/reindexExpand all methods
REST resource for starting/stopping/querying indexing.

Reindex
POST /rest/api/2/reindex
Get reindex info
GET /rest/api/2/reindex
Reindex issues
POST /rest/api/2/reindex/issue
Get reindex progress
GET /rest/api/2/reindex/progress
api/2/reindex/requestExpand all methods
REST resource for querying and executing reindex requests.

Process requests
POST /rest/api/2/reindex/request
Get progress
GET /rest/api/2/reindex/request/{requestId}
Get progress bulk
GET /rest/api/2/reindex/request/bulk
api/2/resolutionExpand all methods
Get resolutions
GET /rest/api/2/resolution
Get resolution
GET /rest/api/2/resolution/{id}
Get paginated resolutions  experimental
GET /rest/api/2/resolution/page
api/2/roleExpand all methods
Create project role
POST /rest/api/2/role
Get project roles
GET /rest/api/2/role
Get project roles by id
GET /rest/api/2/role/{id}
Partial update project role
POST /rest/api/2/role/{id}
Fully update project role
PUT /rest/api/2/role/{id}
Delete project role
DELETE /rest/api/2/role/{id}
Get project role actors for role
GET /rest/api/2/role/{id}/actors
Add project role actors to role
POST /rest/api/2/role/{id}/actors
Delete project role actors from role
DELETE /rest/api/2/role/{id}/actors
api/2/screensExpand all methods
Get all screens
GET /rest/api/2/screens
Get fields to add
GET /rest/api/2/screens/{screenId}/availableFields
Get all tabs
GET /rest/api/2/screens/{screenId}/tabs
Add tab
POST /rest/api/2/screens/{screenId}/tabs
Rename tab
PUT /rest/api/2/screens/{screenId}/tabs/{tabId}
Delete tab
DELETE /rest/api/2/screens/{screenId}/tabs/{tabId}
Add field
POST /rest/api/2/screens/{screenId}/tabs/{tabId}/fields
Get all fields
GET /rest/api/2/screens/{screenId}/tabs/{tabId}/fields
Remove field
DELETE /rest/api/2/screens/{screenId}/tabs/{tabId}/fields/{id}
Move field
POST /rest/api/2/screens/{screenId}/tabs/{tabId}/fields/{id}/move
Update show when empty indicator
PUT /rest/api/2/screens/{screenId}/tabs/{tabId}/fields/{id}/updateShowWhenEmptyIndicator/{newValue}
Move tab
POST /rest/api/2/screens/{screenId}/tabs/{tabId}/move/{pos}
Add field to default screen
POST /rest/api/2/screens/addToDefault/{fieldId}
api/2/searchExpand all methods
Resource for searches.

Search using search request
POST /rest/api/2/search
Search
GET /rest/api/2/search
api/2/securitylevelExpand all methods
Get issuesecuritylevel
GET /rest/api/2/securitylevel/{id}
api/2/serverInfoExpand all methods
Get server info
GET /rest/api/2/serverInfo
api/2/settingsExpand all methods
REST resource for changing the Jira system settings

Set base u r l
PUT /rest/api/2/settings/baseUrl
Get issue navigator default columns
GET /rest/api/2/settings/columns
Set issue navigator default columns
PUT /rest/api/2/settings/columns
api/2/statusExpand all methods
Get statuses
GET /rest/api/2/status
Get status
GET /rest/api/2/status/{idOrName}
Get paginated statuses  experimental
GET /rest/api/2/status/page
api/2/statuscategoryExpand all methods
Get status categories
GET /rest/api/2/statuscategory
Get status category
GET /rest/api/2/statuscategory/{idOrKey}
api/2/terminology/entriesExpand all methods
Enables customizing the default words "epic" and "sprint".

Set terminology entries  experimental
POST /rest/api/2/terminology/entries
Get all terminology entries  experimental
GET /rest/api/2/terminology/entries
Get terminology entry  experimental
GET /rest/api/2/terminology/entries/{originalName}
api/2/universal_avatarExpand all methods
Get avatars
GET /rest/api/2/universal_avatar/type/{type}/owner/{owningObjectId}
Create avatar from temporary
POST /rest/api/2/universal_avatar/type/{type}/owner/{owningObjectId}/avatar
Delete avatar
DELETE /rest/api/2/universal_avatar/type/{type}/owner/{owningObjectId}/avatar/{id}
Store temporary avatar
POST /rest/api/2/universal_avatar/type/{type}/owner/{owningObjectId}/temp
Store temporary avatar using multi part
POST /rest/api/2/universal_avatar/type/{type}/owner/{owningObjectId}/temp
api/2/upgradeExpand all methods
REST resource for executing and querying delayed upgrades.

Run upgrades now
POST /rest/api/2/upgrade
Get upgrade result
GET /rest/api/2/upgrade
api/2/userExpand all methods
Update user  experimental
PUT /rest/api/2/user
Create user  experimental
POST /rest/api/2/user
Remove user  experimental
DELETE /rest/api/2/user
Get user
GET /rest/api/2/user
Add user to application  experimental
POST /rest/api/2/user/application
Remove user from application  experimental
DELETE /rest/api/2/user/application
Find bulk assignable users
GET /rest/api/2/user/assignable/multiProjectSearch
Find assignable users
GET /rest/api/2/user/assignable/search
Create avatar from temporary
POST /rest/api/2/user/avatar
Update user avatar
PUT /rest/api/2/user/avatar
Delete avatar
DELETE /rest/api/2/user/avatar/{id}
Store temporary avatar
POST /rest/api/2/user/avatar/temporary
Store temporary avatar using multi part
POST /rest/api/2/user/avatar/temporary
Get all avatars
GET /rest/api/2/user/avatars
Default columns
GET /rest/api/2/user/columns
Set columns
PUT /rest/api/2/user/columns
Reset columns
DELETE /rest/api/2/user/columns
Get duplicated users count  experimental
GET /rest/api/2/user/duplicated/count
Get duplicated users mapping  experimental
GET /rest/api/2/user/duplicated/list
Change user password  experimental
PUT /rest/api/2/user/password
Find users with all permissions  deprecated
GET /rest/api/2/user/permission/search
Find users for picker
GET /rest/api/2/user/picker
Find users
GET /rest/api/2/user/search
Find users with browse permission
GET /rest/api/2/user/viewissue/search
api/2/user/a11y/personal-settingsExpand all methods
Get a11y personal settings
GET /rest/api/2/user/a11y/personal-settings
api/2/user/anonymizationExpand all methods
Validate user anonymization
GET /rest/api/2/user/anonymization
Schedule user anonymization
POST /rest/api/2/user/anonymization
Validate user anonymization rerun
GET /rest/api/2/user/anonymization/rerun
Schedule user anonymization rerun
POST /rest/api/2/user/anonymization/rerun
Get progress
GET /rest/api/2/user/anonymization/progress
Unlock anonymization
DELETE /rest/api/2/user/anonymization/unlock
api/2/user/propertiesExpand all methods
Get properties keys
GET /rest/api/2/user/properties
Delete property
DELETE /rest/api/2/user/properties/{propertyKey}
Set property
PUT /rest/api/2/user/properties/{propertyKey}
Get property
GET /rest/api/2/user/properties/{propertyKey}
api/2/user/sessionExpand all methods
Delete session
DELETE /rest/api/2/user/session/{username}
api/2/versionExpand all methods
Get paginated versions  experimental
GET /rest/api/2/version
Create version
POST /rest/api/2/version
Move version
POST /rest/api/2/version/{id}/move
Get version
GET /rest/api/2/version/{id}
Update version
PUT /rest/api/2/version/{id}
Delete
DELETE /rest/api/2/version/{id}
Merge
PUT /rest/api/2/version/{id}/mergeto/{moveIssuesTo}
Get version related issues
GET /rest/api/2/version/{id}/relatedIssueCounts
Delete
POST /rest/api/2/version/{id}/removeAndSwap
Get version unresolved issues
GET /rest/api/2/version/{id}/unresolvedIssueCount
Get remote version links by version id
GET /rest/api/2/version/{versionId}/remotelink
Create or update remote version link
POST /rest/api/2/version/{versionId}/remotelink
Delete remote version links by version id
DELETE /rest/api/2/version/{versionId}/remotelink
Get remote version link
GET /rest/api/2/version/{versionId}/remotelink/{globalId}
Create or update remote version link
POST /rest/api/2/version/{versionId}/remotelink/{globalId}
Delete remote version link
DELETE /rest/api/2/version/{versionId}/remotelink/{globalId}
Get remote version links
GET /rest/api/2/version/remotelink
api/2/workflowExpand all methods
REST resource for retrieving workflows.

Get all workflows
GET /rest/api/2/workflow
Update property
PUT /rest/api/2/workflow/{id}/properties
Create property
POST /rest/api/2/workflow/{id}/properties
Delete property
DELETE /rest/api/2/workflow/{id}/properties
Get properties
GET /rest/api/2/workflow/{id}/properties
api/2/workflowschemeExpand all methods
Create scheme
POST /rest/api/2/workflowscheme
Delete scheme
DELETE /rest/api/2/workflowscheme/{id}
Get by id
GET /rest/api/2/workflowscheme/{id}
Update
PUT /rest/api/2/workflowscheme/{id}
Create draft for parent
POST /rest/api/2/workflowscheme/{id}/createdraft
Delete default
DELETE /rest/api/2/workflowscheme/{id}/default
Update default
PUT /rest/api/2/workflowscheme/{id}/default
Get default
GET /rest/api/2/workflowscheme/{id}/default
Delete draft by id
DELETE /rest/api/2/workflowscheme/{id}/draft
Get draft by id
GET /rest/api/2/workflowscheme/{id}/draft
Update draft
PUT /rest/api/2/workflowscheme/{id}/draft
Get draft default
GET /rest/api/2/workflowscheme/{id}/draft/default
Delete draft default
DELETE /rest/api/2/workflowscheme/{id}/draft/default
Update draft default
PUT /rest/api/2/workflowscheme/{id}/draft/default
Get draft issue type
GET /rest/api/2/workflowscheme/{id}/draft/issuetype/{issueType}
Delete draft issue type
DELETE /rest/api/2/workflowscheme/{id}/draft/issuetype/{issueType}
Set draft issue type
PUT /rest/api/2/workflowscheme/{id}/draft/issuetype/{issueType}
Get draft workflow
GET /rest/api/2/workflowscheme/{id}/draft/workflow
Delete draft workflow mapping
DELETE /rest/api/2/workflowscheme/{id}/draft/workflow
Update draft workflow mapping
PUT /rest/api/2/workflowscheme/{id}/draft/workflow
Get issue type
GET /rest/api/2/workflowscheme/{id}/issuetype/{issueType}
Delete issue type
DELETE /rest/api/2/workflowscheme/{id}/issuetype/{issueType}
Set issue type
PUT /rest/api/2/workflowscheme/{id}/issuetype/{issueType}
Get workflow
GET /rest/api/2/workflowscheme/{id}/workflow
Delete workflow mapping
DELETE /rest/api/2/workflowscheme/{id}/workflow
Update workflow mapping
PUT /rest/api/2/workflowscheme/{id}/workflow
api/2/worklogExpand all methods
Get ids of worklogs deleted since
GET /rest/api/2/worklog/deleted
Get worklogs for ids
POST /rest/api/2/worklog/list
Get ids of worklogs modified since
GET /rest/api/2/worklog/updated
auth/1/sessionExpand all methods
Implement a REST resource for acquiring a session cookie.

Current user
GET /rest/auth/1/session
Logout
DELETE /rest/auth/1/session
Login
POST /rest/auth/1/session
auth/1/websudoExpand all methods
Release
DELETE /rest/auth/1/websudo
Atlassian
View cookie preferences