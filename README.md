# Github Mover
This script will allow for the easy migration of an org from a Github enterprise instance to github.com
It uses Github's V3 api to get repo information and copy that to new repo.

By default every new repo is created as private.

#### Not Implemented Yet:
* Issues
* Wiki
* Projects
* Milestones
* Releases

These things are all accessible via the API, but I have not written logic to implement migration of these yet.
PRs welcome :)

## Requirements
This code depends on PyGithub,  you can install it via
```
pip install pygithub
```
or
```
pip install -r requirements.txt
```

You must also have git on your system and have ssh access to both source and destination github orgs / repos.

In order to get all the repo details you need a [Personal Access Token](https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line) from each github instance. 
On the destination it must have permission to create a repo.
## Usage

To make it simple you can put almost everything in a file named `config.ini` and then only provide the source org and destination orgs
 
config.ini:
```ini
[source]
url = github.alaska.edu
token = YourPersonalAccessTokenOnTheSourceInstance
[destination]
url = api.github.com
token = YourPersonalAccessTokenOnTheDestinationInstance
```

Then to migrate every repo from OIT-CSS on github.alaska.edu to ua-oit-se on github.com you could use the following command:
```
python migrate.py -s OIT-CSS -d ua-oit-se -a
```
This will also automatically update the source repo's README.md with a link to the new repo location, instructions for how to update the git config, and set the source repo to archived to prevent new commits after it's been migrated.


If you don't want to use `config.ini` then everything can be provided via arguments:
```
migrate.py [-h] -s SOURCE_ORG -d DESTINATION_ORG
                  [--source_url SOURCE_URL] [--dest_url DEST_URL]
                  [--source_token SOURCE_TOKEN]
                  [--destination_token DESTINATION_TOKEN]

optional arguments:
  -h, --help            show this help message and exit
  -s SOURCE_ORG, --source_org SOURCE_ORG
                        Source Organization
  -d DESTINATION_ORG, --destination_org DESTINATION_ORG
                        Destination Organization
  --source_url SOURCE_URL
                        Source github url
  --dest_url DEST_URL   destination github url
  --source_token SOURCE_TOKEN
                        Source Access Token
  --destination_token DESTINATION_TOKEN
                        Destination Access Token
  -a, --archive         Archive Source Repos with an updated README to the new
                        repo location
```
