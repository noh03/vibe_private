1. Requirement

      Requirement
      This chapter provides information about Requirements.

      Requirement is a description of a feature or functionality of the target product. It is a result of comprehensive analysis of user’s expectations. Creating requirements is the first phase of the testing process.

      If you selected default RTM Issue Types, you can add following ones:

      Functional Requirement
      UI Requirement
      Non-functional Requirement
      Business Requirement
      Note
      For more information about Issue Types configuration, go to: Issue Types.
      Each requirement can be configured as a regular Jira Issue Type and be covered by Test Case.
      You can save your filters. Created filters are available in following sections: Requirements, Test Cases, Test Plans, Test Executions and Defects.
      Add and configured requirement with Requirements and Test Management for Jira app

      Create Requirement
      This chapter provides information about creating Requirements.


      Steps

      To create a requirement:

      Navigate to Project > RTM > Requirements.
      Click +.
      Note
      To add a requirement to the specific folder, click on the folder and then +.
      In the Details section, complete all fields added to the screen.
      Requirements in Jira
      Go to the Test Cases section.
      Select available test cases or create new ones which will cover the requirement.
      Click Add Test Case.
      Add Test Case with Requirements and Test Management for Jira app

      The Add Test Case dialog box appears.
      Select test cases.
      Note
      You can set searching criteria, filter elements and choose which fields will be visible as columns on the list.
      Click Add.
      Add Test Case with Requirements and Test Management for Jira app
      Click Create New Test Case, if you want to add new ones.
      Create new Test Case.
      Note
      Read more about creating Test Cases here.
      Click Create.
      Create new Test Case with Requirements and Test Management for Jira app
      Result

      A new requirement is added to the tree.

      Note
      Requirements can be created as regular Jira issues, by using Create issue dialog box, but then you have to import these issues to the tree.
      You can also add Requirements by clicking Add Requirement in All folder.

      Bulk linking
      This chapter provides information about bulk linking of requirements.

      In order to quickly cover multiple Requirements by multiple Test Cases, we recommend using the bulk linking feature.

      Steps

      1. Navigate to RTM project > Test Management.
      2. Click on relevant Requirements folder.
      3. Select requirements.
      4. Click Cover by TC. The modal window will pop up.
      5. Choose Test Cases.
      6. Click Add.

      Note
      It’s possible to link one or more Test Cases to the currently opened Requirement (View issue screen).
      Result

      Requirements are covered by multiple Test Cases.


2. Test Case
      Test Case
      This chapter provides information about Test Cases.

      Test case is a step-by-step procedure, where the testing path is defined. Test Case determines activities that should be taken to cover Requirement.

      Explore test cases with Requirements and Test Management for Jira app
      Note
      Each Test Case can cover few Requirements.
      Explore test cases with Requirements and Test Management for Jira app
      Note
      Test Cases are included in Test Plans. One Test Case can be linked with several Test Plans.
      Explore test cases with Requirements and Test Management for Jira app
      Note
      Test Cases cannot be executed separately from any Test Plan. It means that every Test Case is executed under the Test Plan.
      It is possible to create a new Test Plan with only one Test Case to execute:
      Navigate to All, click Execute, complete all fields and click Execute.
      For more information, click here.


      Create Test Case
      This chapter provides information about creating Test Cases.


      Tip
      Test Cases can be created as regular Jira issues in Create Issue dialog box. You can also add Test Case by clicking on + in particular folder in the Test Case tree.
      If you haven’t created any new folder yet, go to All.
      To create a Test Case navigate to Project > Test Management > Test Cases. Click +.

      Details
      In the Details section, complete all fields added to the screen:

      Summary
      Issue type
      Description
      Assignee
      Test Plan
      Select folder
      Components
      Priority
      Epic link
      Sprint
      RTM Environment
      Fix Version
      Labels
      Attachments

      Steps
      There are three ways to add steps to your Test Case:

      Create group of steps, where you can create your own step’s procedure
      Link from other TC, where you can copy group of steps from other Test Case
      Import from .CSV file

      Preconditions
      Fill in the Preconditions field if your Test Case requires an additional condition before running the procedure.

      Create a group of steps
      Right after clicking +Create a group of steps, a Default group with first step is added. Now you can:

      Jira Test Case management
      Change step’s group name
      Complete step’s columns
      Tip
      Use the text tools to diversify your text.


      Copy group of steps
      Copy step
      Add Step
      Add Group
      Add Attachment
      Info
      Each step can have own attachments. Attachments can be added after creating an issue.
      Info
      Use drag and drop to reorder the steps or group of steps.
      Use existing steps and implement them to your Test Case with Link steps and Import from CSV buttons.

      Link from other TC
      You don’t have to rewrite Test Case’s steps. Use existing steps from other Test Case and copy them to your new TC:

      Click Link from other TC. A drawer displays.
      Choose Test Case where target steps are stored.
      Click Continue.
      Jira Test Case management solution
      Info
      You can check how many groups of steps are included in Test Case in information box.
      Select groups of steps.
      Click Link.

      As a result, steps from other TC are copied to your Test Case.

      Info
      If you change or edit steps in the root Test Case, they will also change in TCs that reuse it.
      Copied steps are blocked. To edit them you need to unlink TCE group. Click the Unlink steps group icon and make changes in your steps.


      Import from CSV
      Click Import from CSV and choose a .csv file with steps.

      Steps add automatically.

      Example
      Sample file to import can be found here. The file contains three Steps, with columns named Action, Input, Expected result. Each step is located in a separate group.

      Requirements
      Open Test Case’s Requirements tab. There are two ways to add Requirements to your Test Case:

      by adding Requirements, that already exist

      by creating new requirements


      Add Requirement
      Right after clicking on Add Requirement button, a dialog with Requirements display. Select Requirements that will be covered by your Test Case and click Add to confirm the action.


      Create New Requirement
      As soon as you click Create New Requirement, you will be transferred to Requirements tab.

      For further information, navigate to Create Requirement chapter.

      Confirm Test Case creation
      If you have already completed all tabs, click Create to generate your Test Case.


      Bulk linking
      This chapter provides information about bulk linking of Test Cases.

      Test Cases can cover multiple Requirements or fit more than one Test Plan. Instead of connecting them one by one, we recommend using the bulk linking feature.

      Steps

      Navigate to RTM project > Test Management.
      Click on relevant Test Case folder.
      Select Test Cases.
      Click Add to Test Plan or Link to requirement button. The modal window will open.

      Depending on the selected option, choose Test Plans or Requirements that you wish to link with the Test Cases marked before.
      Click Add.

      Note
      It’s possible to link one or more Test Cases to the currently opened Requirement (Create/View issue screen).
      Note
      You can connect opened Test Case with only one Test Plan on the Create/View issue screen.



      Export Test Case
      This chapter provides information on how to export TC with their results.

      The export of Test Cases results is a crucial functionality in regulated industries, but you can also use it to export the TC data from the app. The default report includes only Test Steps of the executed Test Cases. It means that if you need to export the steps of the Test Cases which aren’t executed yet, it’s necessary to perform their execution at least once. The one way of doing this is creating a dedicated Test Plan with all the unexecuted Test Cases.

      Steps
      1. Click on the Test Cases module.
      2. Select Test Cases.
      3. Click the … above the table and choose Export TCE’s results.
      4. When the report is ready, click on its name to download the file.
      Info
      The widget informs about the status of report generation.


      Tip
      Due to technical limitations, a direct link to the attachment is in the JSON file to which you are redirected in the Attachments column.

      Tip
      After exporting, clean your document, so that each Test Case includes only the Test Steps from one Execution. So prepared file can be reused to import the Test Cases back to RTM, for example in case you’d need to migrate from Jira Server to Jira Cloud.



3. Test Plan
      Test Plan
      This section provides information about Test Plans.

      Each testing process needs a Test Plan, where all related Test Cases (and indirectly, its Requirements) are included. It means that Test Plans are summarising all actions during testing procedure.

      Test Plans with Requirements and Test Management for Jira app
      Note
      Test Plan can be executed by Test Execution. You can execute them several times. For example, if you execute Test Plan for few environments.
      You can save your filters. Created filters are available in following sections: Requirements, Test Cases, Test Plans, Test Executions and Defects.

      Create Test Plan
      This section provides information about creating Test Plans.

      Steps
      1. Navigate to Project > RTM > Test Plans.
      2. Click +.
      3. In the Details section, complete all fields added to the screen.
      4. Navigate to Test Cases.
      5. Click Add Test Case.
      The Add Test Case dialog box appears.
      6. Select Test Cases.
      7. Click Add.
      8. Click Create.

      Result
      Test Plan has been created.


      Manage Test Plan
      This section provides information about managing of Test Plans.

      Change order of Test Cases
      You can change order of Test Cases under the Test Plan.

      Steps
      To change the Test Cases order:
      1. Navigate to Project > RTM > Test Plans.
      2. Choose a test plan.
      3. Go to the Test Cases section.
      4. Go to Edit order.
      5. Change the Test Cases order using drag and drop.
      6. Click Accept order.

      If you can’t find the answer you need in our documentation, raise a support request*.
      *Include as much information as possible to help our support team resolve your issue faster.


4. Test Execution
      Test Execution
      This chapter provides information about Test Executions.

      Test Execution is the process of executing Test Plans and monitoring Test Case Execution results.
      Test Execution has the same structure as Test Plan. It contains a list of Test Cases, where you can monitor the current status of Test Case Execution. You can also assign Test Execution to a concrete person.

      In Test Execution you can also check Test Plan Details and set Relations.

      Info
      Test Execution Relations tab also presents current dependencies between Requirements, Test Cases, and Test Plans.
      You can save your filters. Created filters are available in following sections: Requirements, Test Cases, Test Plans, Test Executions, and Defects.


      Execute Test Plan
      This section provides information about executing Test Plans.

      Steps
      To execute Test Plan:
      1. Navigate to Test Management > Test Plans.
      2. Click on the target Test Plan.
      3. Go to the Executions section.
      4. Click Execute Test Plan.

      Note
      You can also navigate to the target folder, select Test Plan and click Execute. Both ways are acceptable.

      The Execute drawer appears.

      5. Complete fields.

      Note
      If you choose here RTM Environment field, the previously selected one in TP or TC will be overwritten.

      6. Click Create.

      Result
      Test Execution based on Test Plan has been created.

      Current status of executions is visible in the Test Plan’s Executions section. Navigate to Test Case Execution and start the procedure.


      Execute Test Case
      This chapter provides information about Test Case Execution.

      Note
      Test Cases are executed only as a part of Test Plan. Test Cases are visible in Test Execution as a list, where you can monitor results or assign each of them to a tester.
      Even if you have one Test Case, it’s mandatory to add it to the Test Plan before execution.
      Test Case Execution is not a regular Jira issue. It means TCEs are not visible in issue navigator and can’t be linked with any issues.


      To start Test Case Execution:
      1. Navigate to Project > RTM > Test Executions.
      2. Click on the target Test Execution.
      3. Choose Test Case Execution

      Each TCE has three tabs: Steps, Details and Relations.

      Steps
      In Steps tab, there are three ways to change steps result:
      1. by Change steps status: tick step’s checkbox to change steps status
      2. by Change status of selected group
      3. by changing step’s status
      You can also:
      4. Fill in Actual result column
      5. Report a new Defect or link TCE with existing one
      6. Upload an Evidence
      7. Upload an Attachment

      Note
      In TCE, Attachment field is a read-only section. You can add Attachments to Test Case before executing Test Plan.

      8. Comment TCE

      Note
      Files are stored in Jira Issue. Evidence’s size depends on your Jira settings. Read more about attachments in Configure file attachments and Attach files and screenshots to issues chapters.


      Details
      In Details tab you can view or configure the following:
      - Execution Details: edit the basic information about the Test Case (Assignee, RTM Environment, Result, Priority)
      - Test Case information (non-editable): information which is based on Test Case from which executions were performed
      - Description (non-editable)

      Relations
      Navigate to Relations tab and view the dependencies between Test Case Execution and Requirements, Test Case, Test Plan, Test Executions and detected Defects. These dependencies are generated automatically from previously configured relations.

      Note
      You can also link Test Case Execution.

      Result
      The Test Case Execution has been configured.

      Info
      At the bottom of every TCE, there’s a floating panel that helps with:
      - Setting the Result of TCE
      - Adding and linking Defect
      - Navigating to previous or next TCE

      Bulk edit of TCE
      Some fields in the Test Case Execution module can be modified with bulk edit functionality. Because TCE objects aren’t native Jira issues (not like the rest of RTM testing elements), there is a dedicated panel that makes multiple editing of Test Casse Executions possible.
      Thanks to this, a user is able to change following fields:
      - Assignee
      - Priority
      - RTM Environment
      - Actual Time
      - Result
      The rest of the fields visible on the Test Case Execution view are blocked for editing and result directly from Test Cases included in a specific Execution.

      Steps
      To edit TCE fields:
      1. Navigate to RTM project > RTM > Test Execution.
      2. Select Test Execution in which you wish to change the fields of included TCE.
      3. Select Test Cases and click Edit.
      4. Change values in selected fields. The ones you prefer not to modify you can leave in Don’t change status.
      5. Click Save.


5. Defect
      This chapter provides information about Defects.

      Defect can be defined as an error or bug that appears during the test execution. As a result of finding such bugs in Test Case Execution, tester creates a defect. Defects are related to the whole Test Case.

      Warning
      - In RTM app Defect is a separate issue type. Make sure you have added defect issue type to the RTM project.
      - Remember, defects tree will be available only if you define project with defects as the same one in which you store requirements and tests. If you choose several projects, the defects tree will not be visible. To check your settings, go to: RTM Configuration > Issue Types > Defects.

      Note
      You can save your filters. Created filters are available in following sections: Requirements, Test Cases, Test Plans, Test Executions, and Defects.

      Defect can have different root causes. It can relate to the current Test Case Execution or be an unclassified bug.

      Those defects, which are clear and easy to classify, can be created from Test Case Execution level. Ones that appear as a separate problem and cannot be linked with any Test Case, are created in the Test Management section (Test Management > Defects > Create Defect).


      Create Defect
      This chapter provides information about creating Defects.


      There are three places where you can create a Defect:
      - in Test Case Execution’s steps
      - in Test Case Execution
      - in Test Management > Defects tab

      Wherever you decide to report a bug or error, you will always have two options:
      - to report a new defect or
      - use already created defect and link it with target TE or TCE

      Info
      Defects are visible in the Relations tab in each related element.

      Create a defect in Test Case Execution’s steps
      To create a Defect, that appeared in TCE step:
      1. Navigate to Project > RTM > Test Executions.
      2. Choose Test Execution.
      3. Click on target Test Case Execution.
      4. In the Steps tab, click + on the right side of Defect section. Create defect dialog appears.

      Note
      You can also link TCE with existing Defect by clicking on link icon. When a Link defect dialog appear, select proper Defects and click Add.

      5. Complete following fields: Summary, Description, Assignee, Select folder, Priority, Components, RTM Environment, Fix version, Labels, Attachments.
      6. Click Create.

      Result
      Defect has been created.

      Note
      You can Open defect or Remove link at any time.

      Create a defect in Test Case Execution
      To create a defect that appeared in TCE:
      1. Navigate to Project > RTM > Test Executions.
      2. Choose Test Execution.
      3. Click on target Test Case Execution.
      4. On a floating bar, expand the Defect list.
      5. Click Create.

      Note
      You can also link TCE with existing Defect by clicking Link. When a Link defect dialog appear, select proper Defects and click Create.

      6. Complete following fields: Summary, Description, Assignee, Select folder, Priority, Components, RTM Environment, Fix version, Labels, Attachments.
      7. Click Create.

      Result
      Defect has been created.

      Create a defect, when a bug or error is difficult to classify
      To create a Defect, which is difficult to classify:
      1. Navigate to Project > RTM > Defects.
      2. Click +.
      a. You can also click Create defect.
      3. In the Details section, complete following fields: Summary, Description, Assignee, Select folder, Priority, Components, RTM Environment, Fix version, Labels, Attachments
      4. Go to the Test Cases section.
      5. Add compatible Test Case.

      Info
      In case of unclassified Test Cases, it’s not mandatory to set a linking. However, we recommend to link it with TC in which defect was discovered.

      6. Click Create.

      Result
      Defect that occurred during testing process has been added to the target Test Case.

      Info
      Defects are visible in the Relations tab in each related element.


