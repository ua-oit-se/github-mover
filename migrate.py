from github import Github
from subprocess import call
import argparse
import configparser


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--source_org', help="Source Organization", required=True)
    parser.add_argument('-d', '--destination_org', help="Destination Organization", required=True)
    parser.add_argument('--source_url', help="Source github url")
    parser.add_argument('--dest_url', help="destination github url", default='https://api.github.com')
    parser.add_argument('--source_token', help="Source Access Token")
    parser.add_argument('--destination_token', help="Destination Access Token")
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

    clone_repos(source_github, dest_github, source_org, dest_org)


def clone_repos(source_github, dest_github, source_org, dest_org):
    source_org = source_github.get_organization(source_org)
    source_repos = source_org.get_repos()
    dest_org = dest_github.get_organization(dest_org)
    dest_repos = dest_org.get_repos()

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

    create_repos(dest_org, repos_to_migrate)
    migrate_repos(source_org, dest_org, repos_to_update)

def migrate_repos(source_org, dest_org, repos):
    pass

def create_repos(org, repos):
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


if __name__ == "__main__":
    main()
