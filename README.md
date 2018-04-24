Sierra MARC full-exports
========================

Code to export marc data from III Sierra ILS.

On this page...
- A description of the code-flow.
- Possible optimizations

---


### Code flow...

The full set of marc records are exported from Sierra twice a week. There are three parts to this code...


#### Determine the last bib

Currently lib/last_bib.py is called by a cron script a few times a day. This produces a json file in a web-accessible directory. One of the json fields contains the last-bib.


#### Set up the tracker

Just before the main processing code is run via cron, the previous tracker is deleted via a separate cron-job. When the main processing code is run via its cron-job, the tracker is checked.
- The first check is to see if it exists. If it doesn't exist, it's created.
- The second check is to see if it contains a last bib. If it doesn't, the last bib is grabbed from the web-accessible last_bib.json url described above.
- The third check is to see if batches have been created. If they haven't been, the tracker uses the last-bib to determine the full-range of bibs, then creates the batches of bib sub-ranges respecting the 2000-bib-range limit for the api.


#### Query the api

- The 'next-batch' bib-range is grabbed from the tracker.
- The api is queried on the bib-range.
- The api returns a file-url for the specified bib-range.
- The file-url is accessed and the file is saved to the target directory with a unique name.
- The tracker is updated indicating that batch is complete.
- The script gets the 'next-batch' bib-range from the tracker, and the cycle continues.


#### Notes

- This code is used by...
    - new-Josiah
        - A fourth step occurs: The processing of the marc-files to extract updates. This is currently accomplished via old code in a private repostory. Those 'update-marc-files' are saved into a directory where a final fifth step occurs. Ruby traject code (in a separate repository) processes each of the update-marc-files, flowing extracted data into solr.
    - tech-services reports ([code](https://github.com/birkin/ts_reporting_project))
        - A cron script triggers code that runs through these marc-files and updates db tables for the web-app.

Back to this code...

- The Sierra api has built-in rate-limiting. When rate-limiting is in effect, instead of the response providing a file-url, it provides a message that rate limiting is in effect with an estimated number of minutes to wait before making the next api call.

- The net effect of this is that after a bunch of files are created/downloaded, the script can run for about five minutes before rate-limiting kicks in.

- The low-tech solution to this that's working is to have the script triggered by cron every 10 minutes during the expected marc-export time-frame, and have each triggered-process run until either rate-limiting kicks in, or until five minutes passes, whichever occurs first.

- The tracker-handling is thus useful for two reasons:
    - For development, or for possible troubleshooting, processing can pick up where it left off easily.
    - It handles the auto-stopping and auto-starting of the script seamlessly.

---


### Possible optimizations

These are in no-particular order; the purpose is to capture ideas that have come up in discussions/brainstorms.

- H.C. is exploring using other features of the Sierra api to get json data-elements instead of marc records, and directly act on that json (utilizing the traject massage-logic) to solrize updates.
    - If this is not implemented, BJD will create code to use the API to directly extract updates that the ruby traject code can operate on.

- It is possible for there to be no records returned for a given range of 2000 bibs, because many bibs have been deleted. This explains why we have a bib _range_ of roughly 8 million bibs, but actually _have_ about 4 million bibs. We've been told that if a bib is deleted, that bib will not return (will not be "undeleted"). Given that, if we were to track deleted bibs, we should be able to significantly reduce the number and increase the efficiency of the queries.

- Currently a file-url is provided by the api even when the number of records to be returned is zero. Instead of downloading that non-useful file, we could instead simply not download it.

- Currently each range-query saves to a separate download file with a unique name. These numerous download files could be combined for more efficient subsequent processing.


---
