# COMP6741_Roboprof

## Group AZ_G_06


### Guide to Repo structure
##### 1. Code to create the: ABKS.ipynb
##### 2. Vocabulary: vocabulary.ttl
##### 3. KB Data:  GraphData.ttl
##### 4. QueryResults: QueryResults.ipynb and pdfOfQueryResults.pdf
##### 5. Courses Folder: Has the lectures and materials for each course
##### 6. Queries and Results: Contains the txt and csv file for each of the given queries and 2 queries that record statistics of the knowledge graph. 
##### 7. Code to extract topics: A2.ipynb
##### 8. Code to run the chatbot: chatbot rasa folder
##### 9. LLM experimentation: UsingLLMsToRewriteAnswers.ipynb


------------------

## Datasets used:
1. CATALOG.csv
2. studentdata.csv
3. CU_SR_OPEN_DATA_CATALOG.csv

## Steps to Create Knowledge Base
The ttl file containing the data for Roboprof was created via the jupyter notebook. To replicate, run the jupyter instance and execute all cells. Make sure the folder structure is maintained. The notebook generates a file called "GraphData.ttl" which is the file containing the triples of all the data

## Code to extract topics
The python file to extract topics was created via jupyter notebook. To replicate, run the jupyter instance and execute all cells. Make sure the folder structure is maintained. The notebook generates a file called "CourseTopicsTxt.txt" which is the file containing the topics extracted from each course.

## Querying the knowledge base
1. Run a fuseki server and open a localhost at port:3030. This opens up the web interface
2. Upload the generated "GraphData.ttl" file as a dataset
3. Run the "QueryResults.ipynb" file cell by cell to get results for each of the given queries. 


## Code to run the chatbot
After you are in the chatbot rasa folder, perform the following steps:
1. rasa train
2. rasa run actions
3. rasa shell

