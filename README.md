# trove-periodicals-data

This dataset was created by checking, correcting, and enriching data about digitised periodicals obtained from the Trove API. Additional metadata describing periodical titles and issues was extracted from the Trove website and used to check the API results. Where titles were wrongly described as issues, and vice versa, the records were corrected. Additional descriptive metadata was also added into the records. Separate CSV formatted data files were created for titles and issues. Finally, the titles and issues data was loaded into an SQLite database for use with Datasette.

These datasets were generated using notebooks in the [trove-journals](https://github.com/GLAM-Workbench/trove-journals/) repository.

For more information and documentation see the [Details of digitised periodicals from the `/magazine/titles` API endpoint](https://glam-workbench.net/trove-journals/periodicals-data-api/) section of the [GLAM Workbench](https://glam-workbench.net).

## Dataset summary
- [titles-issues-added.ndjson](https://github.com/GLAM-Workbench/trove-periodicals-data/raw/main/titles-issues-added.ndjson) (3.8 MB, ndjson)
- [periodical-titles.csv](https://github.com/GLAM-Workbench/trove-periodicals-data/raw/main/periodical-titles.csv) (295.5 kB, text/csv)
- [periodical-issues.csv](https://github.com/GLAM-Workbench/trove-periodicals-data/raw/main/periodical-issues.csv) (9.2 MB, text/csv)
- [periodicals.db](https://github.com/GLAM-Workbench/trove-periodicals-data/raw/main/periodicals.db) (12.3 MB, db)


## Dataset details

### [titles-issues-added.ndjson](https://github.com/GLAM-Workbench/trove-periodicals-data/raw/main/titles-issues-added.ndjson)

|                |                                                                                                                                                                                                                                                                                                                                           |
|:---------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| date harvested | 2026-04-22                                                                                                                                                                                                                                                                                                                                |
| file size      | 3.8 MB                                                                                                                                                                                                                                                                                                                                    |
| format         | ndjson                                                                                                                                                                                                                                                                                                                                    |
| created by     | <a href='https://github.com/GLAM-Workbench/trove-journals/blob/master/periodicals-from-api.ipynb'>Get details of periodicals from the `/magazine/titles` API endpoint</a> ([documentation](https://glam-workbench.net/trove-journals/periodicals-from-api/))                                                                              |
| number of rows | 949                                                                                                                                                                                                                                                                                                                                       |
| description    | This file contains data describing digitised periodicals available from Trove. The titles and issues data was harvested from the Trove API and combined into a single file. Duplicate titles and Commonwealth Parliamentary Papers were removed. Additional data on issues missing from the API results was scraped from Trove web pages. |
| license        | [CC0 Public Domain Dedication](https://creativecommons.org/publicdomain/zero/1.0/)                                                                                                                                                                                                                                                        |



### [periodical-titles.csv](https://github.com/GLAM-Workbench/trove-periodicals-data/raw/main/periodical-titles.csv)

|                |                                                                                                                                                                                                                                                                    |
|:---------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| date harvested | 2026-04-22                                                                                                                                                                                                                                                         |
| file size      | 295.5 kB                                                                                                                                                                                                                                                           |
| format         | text/csv                                                                                                                                                                                                                                                           |
| created by     | <a href='https://github.com/GLAM-Workbench/trove-journals/blob/master/periodicals-enrich-for-datasette.ipynb'>Enrich the list of periodicals from the Trove API</a> ([documentation](https://glam-workbench.net/trove-journals/periodicals-enrich-for-datasette/)) |
| number of rows | 909                                                                                                                                                                                                                                                                |

#### Columns

| description                                                     | name            | type    |
|:----------------------------------------------------------------|:----------------|:--------|
| `nla.obj` identifier for the periodical                         | `id`            | string  |
| title of the periodical                                         | `title`         | string  |
| additional information, eg 'Issues 1-7 (incomplete)'            | `description`   | string  |
| publisher of periodical                                         | `publisher`     | string  |
| url to view digitised periodical in Trove                       | `trove_url`     | string  |
| url to download a zip file containing OCRd text from this title | `download_text` | string  |
| number of digitised issues in Trove                             | `issue_count`   | integer |
| earliest publication date                                       | `start_date`    | date    |
| latest publication date                                         | `end_date`      | date    |
| publication year of first digitised issue                       | `start_year`    | integer |
| publication year of last digitised issue                        | `end_year`      | integer |
| physical description, eg: '2 v; 22 cm'                          | `extent`        | string  |
| locations associated with this periodical                       | `place`         | string  |
| ISSN                                                            | `issn`          | string  |
| link to NLA catalogue                                           | `catalogue_url` | string  |

### [periodical-issues.csv](https://github.com/GLAM-Workbench/trove-periodicals-data/raw/main/periodical-issues.csv)

|                |                                                                                                                                                                                                                                                                    |
|:---------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| date harvested | 2026-04-22                                                                                                                                                                                                                                                         |
| file size      | 9.2 MB                                                                                                                                                                                                                                                             |
| format         | text/csv                                                                                                                                                                                                                                                           |
| created by     | <a href='https://github.com/GLAM-Workbench/trove-journals/blob/master/periodicals-enrich-for-datasette.ipynb'>Enrich the list of periodicals from the Trove API</a> ([documentation](https://glam-workbench.net/trove-journals/periodicals-enrich-for-datasette/)) |
| number of rows | 37016                                                                                                                                                                                                                                                              |

#### Columns

| description                                                   | name                | type    |
|:--------------------------------------------------------------|:--------------------|:--------|
| `nla.obj` identifier for the issue                            | `id`                | string  |
| `nla.obj` identifier for the periodical                       | `title_id`          | string  |
| title of the periodical                                       | `title`             | string  |
| additional issue publication details, eg: 'Volume 1, issue 1' | `description`       | string  |
| issue publication date                                        | `date`              | date    |
| url to view the issue in Trove                                | `url`               | string  |
| number of pages in this issue                                 | `pages`             | integer |
| url to download OCRd text from this issue                     | `text_download_url` | string  |

### [periodicals.db](https://github.com/GLAM-Workbench/trove-periodicals-data/raw/main/periodicals.db)

|                |                                                                                                                                                                                                                                                                                                                                                                                                   |
|:---------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| date harvested | 2026-04-21                                                                                                                                                                                                                                                                                                                                                                                        |
| file size      | 12.3 MB                                                                                                                                                                                                                                                                                                                                                                                           |
| format         | db                                                                                                                                                                                                                                                                                                                                                                                                |
| created by     | <a href='https://github.com/GLAM-Workbench/trove-journals/blob/master/periodicals-enrich-for-datasette.ipynb'>Enrich the list of periodicals from the Trove API</a> ([documentation](https://glam-workbench.net/trove-journals/periodicals-enrich-for-datasette/))                                                                                                                                |
| description    | This SQLite database contains data relating to digitised periodical titles and issues from Trove. It was created for use with Datasette-Lite. There is a foreign key link between the issues and the titles, making it easy to find the issues from any title. Some extra columns have been added to include thumbnails and provide links to search for articles in Trove and download OCRd text. |

## Examples of use

- [Explore in Datasette](https://glam-workbench.net/datasette-lite/?url=https://github.com/GLAM-Workbench/trove-periodicals-data/blob/main/periodicals.db&install=datasette-json-html&install=datasette-template-sql&metadata=https://github.com/GLAM-Workbench/trove-periodicals-data/blob/main/metadata.json)
- [Visualised in the Trove Data Guide](https://tdg.glam-workbench.net/other-digitised-resources/periodicals/overview.html)


----
Created by [Tim Sherratt](https://timsherratt.au) for the [GLAM Workbench](https://glam-workbench.net)