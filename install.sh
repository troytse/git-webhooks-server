#!/usr/bin/env bash

# Get the script directory
if [[ -L ${BASH_SOURCE[0]} ]]; then
    script_dir=$(dirname $(readlink ${BASH_SOURCE[0]}))
else
    script_dir=$(cd $(dirname ${BASH_SOURCE[0]}); pwd -P)
fi
source "${script_dir}/message.sh"

# run as root user
[ $UID != 0 ] && cmd_prefix="sudo " && $(sudo echo -n '')
INFO "Git-Webhooks-Server Installation."

# for uninstall
if [[ $1 = '--uninstall' ]];then
	if [ -f "${script_dir}/installed.env" ]; then
		source "${script_dir}/installed.env"
		QUES_N "Confirm to uninstall? (N/y)" confirm
		if [ ! -z $confirm ] || [[ ${confirm:1} =~ 'Y|y' ]]; then
			$cmd_prefix systemctl stop git-webhooks-server
			$cmd_prefix systemctl disable git-webhooks-server
			if [ -f $bin_path ];then
				INFO_N "Uninstall: ${bin_path}"
				$cmd_prefix rm -f $bin_path
				if [ -f $bin_path ];then WARN " [Fail]"; else INFO " [OK]"; fi
			fi
			if [ -f $conf_path ];then
				INFO_N "Uninstall: ${conf_path}"
				$cmd_prefix rm -f $conf_path
				if [ -f $conf_path ];then WARN " [Fail]"; else INFO " [OK]"; fi
			fi
			if [ -f $service_path ];then
				INFO_N "Uninstall: ${service_path}"
				$cmd_prefix rm -f $service_path
				if [ -f $service_path ];then WARN " [Fail]"; else INFO " [OK]"; fi
			fi
			rm -f "${script_dir}/installed.env"
		fi
	else
		ERR "You have not installed"
	fi
	exit 0
fi

# enter install directory
QUES_N "Enter install directory (default: /usr/local/bin)" bin_path
[ -z $bin_path ] && bin_path='/usr/local/bin'
[ ! -d $bin_path ] && ERR "No such directory: ${bin_path}" && exit 1
bin_path="${bin_path}/git-webhooks-server.py"

# enter configuration directory
QUES_N "Enter configuration directory (default: /usr/local/etc)" conf_path
[ -z $conf_path ] && conf_path='/usr/local/etc'
[ ! -d $conf_path ] && ERR "No such directory: ${conf_path}" && exit 1
conf_path="${conf_path}/git-webhooks-server.ini"

# copy bin file
INFO_N "Installing: ${script_dir}/git-webhooks-server.py => ${bin_path}"
# clean
[ -f $bin_path ] && $cmd_prefix rm -f $bin_path
# copy file and set as executable
$cmd_prefix cp -i "${script_dir}/git-webhooks-server.py" $bin_path
$cmd_prefix chmod +x $bin_path
if [ -f $bin_path ];then
	INFO " [OK]"
	echo "bin_path=${bin_path}" >> "${script_dir}/installed.env"
else
	ERR " [Fail]"
	exit 1
fi

INFO_N "Installing: ${script_dir}/git-webhooks-server.ini.sample => ${conf_path}"
# clean
[ -f $conf_path ] && $cmd_prefix rm -f $conf_path
# copy file
$cmd_prefix cp "${script_dir}/git-webhooks-server.ini.sample" $conf_path
if [ -f $conf_path ];then
	INFO " [OK]"
	echo "conf_path=${conf_path}" >> "${script_dir}/installed.env"
else
	ERR " [Fail]"
	exit 1
fi

#
if command -v systemctl > /dev/null; then
	QUES "Install as systemd service? (Y/n)" confirm
	if [ -z $confirm ] || [[ ${confirm:1} =~ 'Y|y' ]]; then
		service_dir="/usr/lib/systemd/system"
		service_path="${service_dir}/git-webhooks-server.service"
		INFO_N "Installing: ${script_dir}/git-webhooks-server.service.sample => ${service_path}"
		# clean
		[ -f $service_path ] && $cmd_prefix rm -f $service_path
		# copy file
		[ ! -d $service_dir ] && $cmd_prefix mkdir -p $service_dir
		$cmd_prefix cp -i "${script_dir}/git-webhooks-server.service.sample" $service_path
		# replace the service start command
		$cmd_prefix sed -i "s/REPLACE_BY_INSTALL/${bin_path//\//\\\/} -c ${conf_path//\//\\\/}/g" $service_path
		if [ -f $service_path ];then
			INFO " [OK]"
			echo "service_path=${service_path}" >> "${script_dir}/installed.env"
		else
			ERR " [Fail]"
			exit 1
		fi
		# startup
		QUES "Enable and startup the service? (Y/n)" confirm
		if [ -z $confirm ] || [[ ${confirm:1} =~ 'Y|y' ]]; then
			$cmd_prefix systemctl enable git-webhooks-server
			$cmd_prefix systemctl start git-webhooks-server
		fi
	fi
fi
