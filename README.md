# Agent Plane

Create, run, and manage agents without code or complex setup. Local-first and portable.

## Setup

We use [mise](https://mise.jdx.dev/) to set up tools.

Install `mise` to make the commands shown in this section available.

### Initialisation

Run this command before starting development:

```
mise run init  # Set up for development (install dependencies and install pre-commit hooks)
```

### Development Commands

```
mise run dev     # start development server
mise run test    # run unittests
mise run mmm     # make migrations and migrate
```

### Committing

```
mise run format  # lint and format
```
