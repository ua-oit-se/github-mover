from github import Auth, Github, GithubException
from subprocess import call
import argparse
import configparser
import platform
import subprocess


# Determines if repository exists at the destination or not
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


# Migrates repositories to the destination (use when repos do not exist at the destination)
def migrate_repos(entity, repos):
    current_os = platform.system()

    for repo in repos:
        print('Creating Repo %s...' % repo.name)
        homepage = repo.homepage if repo.homepage else ''
        description = repo.description if repo.description else ''
        new_repo = entity.create_repo(repo.name, description=description, homepage=homepage, private=True,
                                   has_issues=repo.has_issues, has_wiki=repo.has_wiki, has_downloads=repo.has_downloads,
                                   has_projects=repo.has_projects, auto_init=False)
        call('git clone %s --bare' % repo.ssh_url, shell=True)
        call('git remote add destination %s' % new_repo.ssh_url, shell=True, cwd=repo.name + '.git')
        call('git push destination --mirror', shell=True, cwd=repo.name + '.git')

        if current_os == 'Windows':
            call('rmdir /s /q %s.git' % repo.name, shell=True)
        elif current_os == 'Linux':
            call('rm -rf %s.git' % repo.name, shell=True)


# Updates repositories at the destination (use when repos do exist at the destination)
def update_repos(repos, dest_repos):
    current_os = platform.system()

    for repo in repos:
        print('Updating Repo %s...' % repo.name)
        overwrite, prompt_user = False, False

        # Identify if source or destination has most recent updates or if they have divergent changes
        activity_source, activity_dest = False, False
        call('git clone %s' % repo.ssh_url, shell=True)

        dest_repo = ''
        for drepo in dest_repos:
            if repo.name == drepo.name:
                dest_repo = drepo

        call('git remote add remote-b %s' % dest_repo.ssh_url, shell=True, cwd=repo.name)
        call('git fetch --all', shell=True, cwd=repo.name)

        result_a = subprocess.run(['git', 'symbolic-ref', '--short', 'refs/remotes/origin/HEAD'], cwd=repo.name, capture_output=True, text=True, check=True)
        head_a = result_a.stdout.strip().split('/', 1)[1]

        result_b = subprocess.run(['git', 'symbolic-ref', '--short', 'refs/remotes/remote-b/HEAD'], cwd=repo.name, capture_output=True, text=True, check=True)
        head_b = result_b.stdout.strip().split('/', 1)[1]

        remotes_a = 'remote-b/%s..origin/%s' % (head_b, head_a)
        log_a = subprocess.run(['git', 'log', remotes_a, '--oneline'], cwd=repo.name, capture_output=True, text=True, check=True)
        if log_a.stdout.strip() != '':
            activity_source = True

        remotes_b = 'origin/%s..remote-b/%s' % (head_a, head_b)
        log_b = subprocess.run(['git', 'log', remotes_b, '--oneline'], cwd=repo.name, capture_output=True, text=True, check=True)
        if log_b.stdout.strip() != '':
            activity_dest = True

        if current_os == 'Windows':
            call('rmdir /s /q %s' % repo.name, shell=True)
        elif current_os == 'Linux':
            call('rm -rf %s' % repo.name, shell=True)

        if activity_source and not activity_dest:
            print('New activity found at source; no new activity found at destination. Overwriting destination.')
            overwrite = True
        elif activity_source and activity_dest:
            print('New activity found at source; new activity found at destination. Deferring to user.')
            prompt_user = True
        elif not activity_source and activity_dest:
            print('No new activity found at source; new activity found at destination. Deferring to user.')
            prompt_user = True
        elif not activity_source and not activity_dest:
            print('No new activity found at source; no new activity found at destination. No action needed.')

        # Prompt user to overwrite or skip repository
        if prompt_user:
            response = input('Would you like to overwrite the destination repository? (Y/N): ')
            
            # Any response other than 'Y', 'y', 'YES', & 'yes' will be understood as a 'no'
            if response.lower() in ['y', 'yes']:
                overwrite = True
                print('Overwriting destination.')
            else:
                print('Skipping %s...' % repo.name)

        if overwrite:
            call('git clone %s --bare' % repo.ssh_url, shell=True)
            call('git remote set-url origin %s' % dest_repo.ssh_url, shell=True, cwd=repo.name + '.git')
            new_homepage = repo.homepage if repo.homepage else ''
            new_description = repo.description if repo.description else ''
            dest_repo.edit(description=new_description, homepage=new_homepage)
            call('git push --mirror', shell=True, cwd=repo.name + '.git')

            if current_os == 'Windows':
                call('rmdir /s /q %s.git' % repo.name, shell=True)
            elif current_os == 'Linux':
                call('rm -rf %s.git' % repo.name, shell=True)


# Updates the README with an archival message
def update_readme(repo, dest):
    readme = None
    info = """# This Repo Has Moved!

This repo is now located at [{url}]({url})

Use the following command to point your local repo at it:

```
git remote set-url origin git@github.com:{org_name}/{repo_name}.git
```    
""".format(url='https://github.com/%s/%s' % (dest, repo.name), entity_name=dest, repo_name=repo.name)

    print('\tUpdating README...')
    try:
        for content in repo.get_contents(''):  # get files at the root of the repo
            if content.path.lower() == 'readme.md':
                print('\t\tExisting README.md found, prepending info')
                readme = content
                break
    except GithubException as e:
        print(e)
    # No README.md
    if readme is not None:
        info += readme.decoded_content.decode()
        repo.update_file('README.md', 'Update: Update README with new repo location before archive', info, readme.sha)
    else:
        print('\tNo README.md found, creating one with info')
        repo.create_file('README.md', 'Update: Update README with new repo location before archive', info)


# Marks repos as archived
def archive_repos(repos, dest):
    for repo in repos:
        if not repo.archived:
            print('Archiving Repo %s' % repo.full_name)
            update_readme(repo, dest)
            repo.edit(archived=True)
            print('Success')


if __name__ == '__main__':
    # Retrieve arguments passed in
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--source', help='Source', required=True)
    parser.add_argument('-d', '--destination', help='Destination', required=True)
    parser.add_argument('--source_url', help='Source github url')
    parser.add_argument('--dest_url', help='destination github url', default='https://api.github.com')
    parser.add_argument('--source_token', help='Source Access Token')
    parser.add_argument('--dest_token', help='Destination Access Token')
    parser.add_argument('-a', '--archive', action='store_true', help='Archive Source Repos with an updated README to the new repo location')
    parser.add_argument('-o', '--organization', action='store_true', help='Organization-specific repositories, default is user-specific repositories')
    args = parser.parse_args()

    ORG = False
    if args.organization:
        ORG = True

    # Retrieve arguments from config.ini
    config = configparser.ConfigParser()
    config.read('config.ini')

    source_user, dest_user = '', ''
    source_org, dest_org = '', ''
    source_token, dest_token = '', ''

    if ORG:
        source_org = args.source
        dest_org = args.destination
        source_token = config['org_source']['token']
        dest_token = config['org_destination']['token']
        source_url = config['org_source']['url']
        dest_url = config['org_destination']['url']
    else:
        source_user = args.source
        dest_user = args.destination
        source_token = config['user_source']['token']
        dest_token = config['user_destination']['token']
        source_url = config['user_source']['url']
        dest_url = config['user_destination']['url']

    # Using the flags for source_url, dest_url, source_token, and dest_token overrides config.ini
    if args.source_token:
        source_token = args.source_token
    if args.dest_token:
        dest_token = args.dest_token
    if args.source_url:
        source_url = args.source_url
    if args.dest_url:
        dest_url = args.dest_url

    # Stop if required information wasn't provided
    if not source_url or not dest_url or not source_token or not dest_token:
        print('Could not find config file or not all arguments provided.')
        print('Must have the source URL, destination URL, source token, and destination token')
        exit(1)

    # Assemble URLs
    if not source_url.startswith('http'):
        source_url = 'https://' + source_url
    if not source_url.endswith('/api/v3'):
        source_url += '/api/v3'
    if not dest_url.startswith('http'):
        dest_url = 'https://' + dest_url
    if dest_url != 'https://api.github.com' and not dest_url.endswith('/api/v3'):
        dest_url += '/api/v3'

    source_github = Github(base_url=source_url, auth=Auth.Token(source_token))
    dest_github = Github(base_url=dest_url, auth=Auth.Token(dest_token))

    # Identify relevant repositories
    source_repos, dest_repos = None, None
    if ORG:
        source_org = source_github.get_organization(source_org)
        source_repos = source_org.get_repos()
        dest_org = dest_github.get_organization(dest_org)
        dest_repos = dest_org.get_repos()
    else:
        source_user = source_github.get_user()
        source_repos = source_user.get_repos(type="owner")
        dest_user = dest_github.get_user()
        dest_repos = dest_user.get_repos()

    # Compare source repositories to destination repositories
    repos_to_migrate, repos_to_update = compare_repos(source_repos, dest_repos)

    # Perform migrations
    if ORG:
        if repos_to_migrate != []:
            migrate_repos(dest_org, repos_to_migrate)

        if repos_to_update != []:
            update_repos(repos_to_update, dest_repos)
    else:
        if repos_to_migrate != []:
            migrate_repos(dest_user, repos_to_migrate)

        if repos_to_update != []:
            update_repos(repos_to_update, dest_repos)

    if args.archive:
        archive_repos(source_repos, args.destination)
