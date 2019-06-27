# Application of data science techniques on news articles about LGBT issues dating from 2000 through 2019
The NLP News Articles repository applies Data Science techniques (specially NLP and clustering) to a corpus of 250K text articles collected from online sources. The corpus mostly includes news articles, but there are also editorial and opinion pieces, community announcements and blog posts, all of which revolve around the topic of LGBT issues. The articles were originally collected and posted by the moderator of two different online news groups, from year 2000 through 2019. 

The articles were downloaded, with permission of the admin/owner who manages both groups, from Yahoo! Groups (Corpus 1) and Groups IO (Corpus 2). Because the downloading process was based on web-scraping techniques, great care was placed as to not overload the servers where the material is published, by artificially delaying the page request times. Thus, the bulk of the download was conducted at the end of 2017 over a period of two months, for articles ranging from year 2000 through 2017; then, the remaining articles were collected during the first two months of 2019. The last article dates to February 2019. 

Corpus 1 was started in mid-2000 and was closed by the moderator in 2015. Corpus 2 went live in early 2002 and, in January 2019, the moderator stopped adding new content. During the initial data exploration, a third corpus (Corpus 3) was discovered embedded in Corpus 1, so it had to be separated and the data cleaned.

The first step is to remove all article duplicates, caused by cross-posting and then create a single corpus for analysis beased on the unique articles. All articles were dowloaded in HTML format, and extensive cleaning was applied in order to extract the useful information. From the information extracted from each article, various tags were created for future classification. Techniques in Natural Language Processing (NLP) are used, and clustering is performed using unsupervised machine learning (K-Means clustering). 

For more detailed information about the flow of this project, see the file named Summary of Project Steps.

Once copyright issues are cleared legally, the original articles will be made available for public access. Howvever, I can point researchers and institutions to data sources, if contacted directly. 
