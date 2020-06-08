#!/usr/bin/env bash
[ -z $script_dir ] && exit 1

# info
INFO()
{
    echo -e "\033[32;1m$1\033[37;0m"
}
INFO_N()
{
    echo -ne "\033[32;1m$1\033[37;0m"
}
# warning
WARN()
{
    echo -e "\033[1;33m$1\033[37;0m"
}
WARN_N()
{
    echo -ne "\033[1;33m$1\033[37;0m"
}
# error
ERR()
{
    echo -e "\033[31;1m$1\033[37;0m"
}
ERR_N()
{
    echo -ne "\033[31;1m$1\033[37;0m"
}
# question
QUES()
{
	echo -e "\033[34;1m$1:\033[37;0m"
    read $2
}
QUES_N()
{
	echo -ne "\033[34;1m$1:\033[37;0m"
    read $2
}
