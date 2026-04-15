# Introductory Git Walkthrough

## Table of Contents
1. [Introduction](#introduction)
2. [Why Use Version Control?](#why-use-version-control)
3. [Installation](#installation)
4. [Initial Configuration](#initial-configuration)
5. [Basic Git Workflow](#basic-git-workflow)
6. [Working with Remote Repositories](#working-with-remote-repositories)
7. [Handling Merge Conflicts](#handling-merge-conflicts)
8. [Additional Important Commands](#additional-important-commands)

## Introduction
Git is the industry-standard version control system used by developers worldwide. This guide will help you get started with Git fundamentals.

## Why Use Version Control?
- **Version History**: Track and restore previous versions of your code
- **Collaboration**: Enable multiple developers to work on the same project
- **Branching**: Develop features independently without affecting the main codebase
- **Backup**: Store code safely on remote servers
- **Code Review**: Facilitate peer review processes
- **Experimentation**: Try new ideas without risking stable code

![Local Version Control](https://git-scm.com/book/en/v2/images/local.png)
![Centralized Version Control](https://git-scm.com/book/en/v2/images/centralized.png)

## Installation

### Windows
1. Download Git from [git-scm.com/download/win](https://git-scm.com/downloads/win)
2. Run installer with default settings
3. Verify installation: Open Command Prompt and type `git --version`

For Windows, it is recommended to use the installed Git bash in order to follow the rest of the tutorial.

For Mac, I'd recommend the terminal

For Linux, you already know what to use

### macOS
```bash
# Using Homebrew (Recommended)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install git

# OR download from git-scm.com/download/mac
```

### Linux
```bash
# Ubuntu/Debian
sudo apt-get install git

# Fedora
sudo dnf install git

# CentOS
sudo yum install git
```

## Initial Configuration
```bash
# Set your identity
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## Basic Git Workflow

### 1. Initialize a Repository
```bash
mkdir my-project
cd my-project
git init
```

### 2. Create and Track Files
```bash
# Create a file
echo "Hello, Git" > test.txt

# Check status
git status

# Stage files
git add test.txt    # Single file
git add .           # All files

# Check status
git status

# Commit changes
git commit -m "Initial commit"
```

### 3. View History
```bash
# View commit history
git log

# View specific commit
git show <commit-hash>

# View changes in working directory
git diff
```


## Handling Merge Conflicts

Merge conflicts happen when there are two conflicting changes in different locals or branches.

This will likely happen at least once when working in a team, and can be frustrating to fix.

We will work through an example about how to resolve this.

1. First, create a new text file (let's say `example.txt`) in your master/main branch:

```bash
echo "This is the original line" > example.txt
git add example.txt
git commit -m "Initial commit"
```

2. Create and checkout a new branch:
```bash
git checkout -b feature-branch
```

3. Modify the text file in feature-branch:
```bash
echo "This is the feature branch change" > example.txt
git add example.txt
git commit -m "Change in feature branch"
```

4. Switch back to master/main branch:
```bash
git checkout master  # or main
```

5. Make a different change to the same line in the text file:
```bash
echo "This is the master branch change" > example.txt
git add example.txt
git commit -m "Change in master branch"
```

6. Now try to merge the feature branch:
```bash
git merge feature-branch
```

You should see a merge conflict like this:
```
Auto-merging example.txt
CONFLICT (content): Merge conflict in example.txt
Automatic merge failed; fix conflicts and then commit the result.
```

7. Open up the file with conflicts.

The content of example.txt will look something like this:
```
<<<<<<< HEAD
This is the master branch change
=======
This is the feature branch change
>>>>>>> feature-branch
```

To resolve the conflict:
1. Open the file
2. Choose which version you want to keep (or combine them)
3. Remove the conflict markers (<<<<<<< HEAD, =======, and >>>>>>> feature-branch)
4. Save the file
5. Add and commit the changes:
```bash
git status # view status

git add example.txt
git commit -m "Resolved merge conflict"

git status # should say "nothing to commit"
```

Nice Job! You now know the basics of Git! Below are some other helpful commands.

## Additional Important Commands
```bash
# Create and switch to new branch
git checkout -b branch-name

# Switch branches
git checkout branch-name

# List branches
git branch

# Delete branch
git branch -d branch-name
```

Remember: Practice these commands in a test repository to become comfortable with them.


Great! Now that we know the basics of Git, lets push it to the cloud so people can work on it from anywhere!

## Working with Remote Repositories

We can authenticate with GitHub using access tokens (recommended) or ssh keys (more advanced)

### Setting up GitHub
1. Create account on [GitHub](https://github.com)
2. Create new repository
3. Save the repository url found under the code dropdown for https.
This should look like https://github.com/username/repo.git

3. Getting access to the remote:
### Setting up GitHub Personal Access Token (Classic)
1. Go to GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)
2. Click "Generate new token (classic)"
3. Give your token a name/note
4. Select token expiration time
5. Select required scopes (permissions):
   - `repo` (Full control of private repositories)
   - Other scopes as needed
6. Click "Generate token"
7. **Important**: Copy and save the token immediately (you won't see it again!)
8. When performing git actions that need auth (clone push etc) use the access token as your password, with your username as your username

**Security Notes:**
- Keep your token secure like a password

### Using SSH Keys
3. Set up SSH key:
```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your.email@example.com"

# Copy public key
cat ~/.ssh/id_ed25519.pub
```
4. Add SSH key to GitHub account settings

### Connecting Local to Remote

Eventually, you will likely want to push your repo to the internet so that other people can work on it and see you code!

We will use GitHub (the most common remote VCS), although there are other options available.

**Pushing a local git repo to a remote**
```bash
# Add remote repository
git remote add origin <repository-url>

# Push to remote
git push -u origin main
```

**Cloning a remote repo to your local**
```bash
# Clone existing repository
git clone <repository-url>

# Pull changes
git pull
```

Awesome! Now you should see your code on GitHub! If you don't see this or have any questions please ask me!



This guide should give you a solid foundation for using Git. For more advanced topics, consult the [Pro Git Book](https://git-scm.com/book/en/v2).
