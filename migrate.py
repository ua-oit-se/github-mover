from github import Github, GithubException
from subprocess import call
import argparse
import configparser


# github.com access token: 8d45329e88a535d883e995dbbd19327922f3dda4

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--source_org', help="Source Organization", required=True)
    parser.add_argument('-d', '--destination_org', help="Destination Organization", required=True)
    parser.add_argument('--source_url', help="Source github url")
    parser.add_argument('--dest_url', help="destination github url", default='https://api.github.com')
    parser.add_argument('--source_token', help="Source Access Token")
    parser.add_argument('--destination_token', help="Destination Access Token")
    parser.add_argument('-a', '--archive', action="store_true", help="Archive Source Repos with an updated README to the new repo location")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read("config.ini")
    source_url = config["source"]["url"]
    dest_url = config["destination"]["url"]
    source_token = config["source"]["token"]
    dest_token = config["destination"]["token"]
    source_org = args.source_org
    dest_org = args.destination_org

    if args.source_url:
        source_url = args.source_url
    if args.dest_url:
        dest_url = args.dest_url
    if args.source_token:
        source_token = args.source_token
    if args.destination_token:
        dest_token = args.destination_token

    if not source_url or not dest_url or not source_token or not dest_token:
        print("Could not find config file or not all arguments provided.")
        print("Must have the source URL, destination URL, source token, and destination token")
        exit(1)

    if not source_url.startswith("http"):
        source_url = 'https://' + source_url
    if not source_url.endswith('/api/v3'):
        source_url += '/api/v3'
    if not dest_url.startswith("http"):
        dest_url = 'https://' + dest_url
    if dest_url != 'https://api.github.com' and not dest_url.endswith('/api/v3'):
        dest_url += '/api/v3'

    source_github = Github(base_url=source_url, login_or_token=source_token)
    dest_github = Github(base_url=dest_url, login_or_token=dest_token)
    source_org = source_github.get_organization(source_org)
    source_repos = source_org.get_repos()
    dest_org = dest_github.get_organization(dest_org)
    dest_repos = dest_org.get_repos()

    repos_to_migrate, repos_to_update = compare_repos(source_repos, dest_repos)

    create_repos(dest_org, repos_to_migrate, archive=args.archive)

    if args.archive:
        archive_repos(source_repos, args.destination_org)

def compare_repos(source_repos, dest_repos):

    repos_to_update = []
    repos_to_migrate = []

    for repo in source_repos:
        need_to_migrate = True
        for drepo in dest_repos:
            if repo.name == drepo.name:
                repos_to_update.append(repo)
                need_to_migrate = False
                break
        if need_to_migrate:
            repos_to_migrate.append(repo)

    return repos_to_migrate, repos_to_update


def migrate_repos(source_org, dest_org, repos):
    pass


def create_repos(org, repos, archive=False):
    for repo in repos:
        print("Creating Repo %s..." % repo.name)
        homepage = repo.homepage if repo.homepage else ''
        description = repo.description if repo.description else ''
        new_repo = org.create_repo(repo.name, description=description, homepage=homepage, private=True,
                                   has_issues=repo.has_issues, has_wiki=repo.has_wiki, has_downloads=repo.has_downloads,
                                   has_projects=repo.has_projects, auto_init=False)
        call('git clone %s --bare' % repo.ssh_url, shell=True)
        call('git remote add destination %s' % new_repo.ssh_url, shell=True, cwd=repo.name + '.git')
        call('git push destination --mirror', shell=True, cwd=repo.name + '.git')
        call('rm -rf %s.git' % repo.name, shell=True)


def update_readme(repo, dest_org):
    readme = None
    info = """# This Repo Has Moved!

This repo is now located at [{url}]({url})
To point your current repo at it type:

```
git remote set-url origin git@github.com:{org_name}/{repo_name}.git
```    
""".format(url="https://github.com/%s/%s" % (dest_org, repo.name), org_name=dest_org, repo_name=repo.name)

    print("\tUpdating README...")
    try:
        for content in repo.get_contents(""):  # get files at the root of the repo
            if content.path.lower() == "readme.md":
                print("\t\tExisting README.md found prepending info")
                readme = content
                break
    except GithubException as e:
        print(e)
    # No README.md
    if readme is not None:
        info += readme.decoded_content.decode()
        repo.update_file('README.md', "Update: Update README with new repo location before archive", info, readme.sha)
    else:
        print("\tNo README.md found, creating one with info")
        repo.create_file('README.md', "Update: Update README with new repo location before archive", info)



def archive_repos(repos, dest_org):
    for repo in repos:
        if not repo.archived:
            print("Archiving Repo %s" % repo.full_name)
            update_readme(repo, dest_org)
            repo.edit(archived=True)
            print("Success")


if __name__ == "__main__":
    main()
