# Simple Git Webhooks Server

[README](README.md) | [中文说明](README.zh.md)

#### Introduction
- Implemented with Python 3.
- Supports Github, Gitee, Gitlab, and custom repositories.
- Support custom working directory and command for different repositories.
- Support to install as the Systemd service.

#### Installation

- Clone or download this repository to any directory.
- Run `./install.sh` to install.
```shell
git clone https://github.com/troytse/git-webhooks-server.git
cd git-webhooks-server
./install.sh
```
![install](doc/install.png)

#### Uninstallation

```shell
cd git-webhooks-server
./install.sh --uninstal
```
![uninstall](doc/uninstall.png)

#### Usage

- Add the following settings to your configuration file:
```ini
# match the full name of your repository
[your_name/repository]
# working directory
cwd=/path/to/your/repository
# the command executes on received the notification.
cmd=git fetch --all & git reset --hard origin/master & git pull
```

- Restart the service
```shell
systemctl restart git-webhooks-server
```

- Add webhook in the repository settings.
  - **Github**:

  ![github](doc/github.png)
  ![github-success](doc/github-success.png)

  - **Gitee**:

  ![gitee](doc/gitee.png)
  ![gitee-success](doc/gitee-success.png)

  - **Gitlab**:

  ![gitlab](doc/gitlab.png)
  ![gitlab-success](doc/gitlab-success.png)

  - **Custom**: 
  - for custom webhooks sources, you need to change the configuration file like follows:
  ```ini
  [custom]
  # used to identify the source
  header_name=X-Custom-Header
  header_value=Custom-Git-Hookshot
  # used to match the secret
  header_token=X-Custom-Token
  # the path of the repository name in the json request data.
  name_path=project.path_with_namespace
  # only supports text token verification
  verify=True
  secret=123456
  ```
  - Handler accepts POST data types with `application/json` or `application/x-www-form-urlencoded` (you can refer to the guide about request in [Github](https://developer.github.com/webhooks/event-payloads/#example-delivery) / [Gitee](https://gitee.com/help/articles/4186) / [Gitlab](https://gitlab.com/help/user/project/integrations/webhooks#push-events)), data is like this:
  ```json
  {
    "project": {
      "path_with_namespace": "your_name/repository"
    }
  }
  ```
  ![custom-header](doc/custom-header.png)
  ![custom-body](doc/custom-body.png)
  ![custom-response](doc/custom-response.png)

#### Configuration

- Default configuration file: `/usr/local/etc/git-webhooks-server.ini`.
- You can modify it after the installation.
- A typical configuration file is as follows:

```ini
[server]
address=0.0.0.0
port=6789
log_file=/var/log/git-webhooks-server.log

[github]
verify=True
secret=123456

[gitee]
verify=True
secret=123456

[gitlab]
verify=True
secret=123456

[custom]
header_name=X-Custom-Header
header_value=Custom-Git-Hookshot
header_token=X-Custom-Token
name_path=project.path_with_namespace
verify=True
secret=123456

[your_name/repository]
cwd=/path/to/your/repository
cmd=git fetch --all & git reset --hard origin/master & git pull

[your_name/sample]
cwd=/path/to/sample
cmd=git fetch --all & git reset --hard origin/master & git pull
```
