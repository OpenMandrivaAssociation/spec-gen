#!/usr/bin/python3

__author__ = 'Andrey Soloviev, Denis Silakov'
__copyright__ = 'Copyright 2014, ROSA Company'

import zipfile
import tarfile
import os
import sys
import argparse
import tempfile
import subprocess
import shutil

# Requirements extracted from CMake files
requiresCMake = []

requiresConfigure = []
commandsConfigureLIB = []
commandsConfigureLibArgs = [] # some useful arguments from commands

# Archive format type
formatType = 0

# Tag value for the spec
Name = ""
Version = ""
Summary = ""
Group = ""
URL = ""
License = ""

providesHash = {}

def openArchiveFile(path, to_dir):
    if path.endswith('.zip'):
        opener, mode = zipfile.ZipFile, 'r'
    elif path.endswith('.tar.gz') or path.endswith('.tgz'):
        opener, mode = tarfile.open, 'r:gz'
    elif path.endswith('.tar.bz2') or path.endswith('.tbz'):
        opener, mode = tarfile.open, 'r:bz2'
    elif path.endswith('.tar.xz') or path.endswith('.txz'):
        opener, mode = tarfile.open, 'r:xz'
    else:
        print("Could not extract " + path + " as no appropriate extractor is found")
        exit(1)

    cwd = os.getcwd()
    try:
        archive_file = opener(path, mode)
        try:
            archive_file.extractall(to_dir)
            print("Archive " + path + " is unpacked successfully to " + to_dir)
        except:
            print("Problems with unpacking")
        finally: archive_file.close()

    except:
        print("Problems with archive opening")
    finally:
        os.chdir(cwd)

def defineFormat(path):
    formatType = 0
    if path.endswith('.zip'):
        formatType = 1
    elif path.endswith('.tar.gz') or path.endswith('.tgz'):
        formatType = 2
    elif path.endswith('.tar.bz2') or path.endswith('.tbz'):
        formatType = 3
    elif path.endswith('.tar.xz') or path.endswith('.txz'):
        formatType = 4
    else:
        print("Could not extract " + path + " as no appropriate extractor is found")
    return formatType

def defineNameAndVersion(path, formatType):
    nameM = path.split('-')
    name = ""
    for word in nameM:
        if (name == ""):
            name += word
            name += '-'
            continue
        if (word[0] >= '0' and word[0] <= '9' ):
            break
        else:
            name += word
            name += '-'
    nameM = path.split(name)
    if (formatType >= 2 and formatType <= 4):
         versionM = nameM[1].split(".tar")
    else:
         versionM = nameM[1].split(".zi")
    Version = versionM[0]
    # deleting path in name
    myListName = list(name)
    del myListName[len(name) - 1] # deleting "-" in the end of name
    name = ""
    for char in myListName:
        name += char
    if (name.find("\\") > -1):
        Name = name.split("\\")
    else:
        Name = name.split("/")

    return Name[-1], Version

# try to find a package that satisfies given requirement
def search_req(arg):
    if arg == "":
        return ""

    if arg in providesHash:
        return ""

    providesHash[arg] = 1

    pkgconfig = subprocess.call(["urpmq", "--whatprovides", "'pkgconfig(" + str(arg) + ")'"])
    if not pkgconfig:
        # pkgconfig is zero - this means that urpmq found something
        return "pkgconfig(" + str(arg) + ")"

    pkgconfig = subprocess.call(["urpmq", "--whatprovides", "'pkgconfig(lib" + str(arg) + ")'"])
    if not pkgconfig:
        # pkgconfig is zero - this means that urpmq found something
        return "pkgconfig(lib" + str(arg) + ")"

    devel = subprocess.call(["urpmq", "--whatprovides", str(arg) + "-devel"])
    if not devel:
        return str(arg) + "-devel"

    devel = subprocess.call(["urpmq", "--whatprovides", "lib" + str(arg) + "-devel"])
    if not devel:
        return "lib" + str(arg) + "-devel"

    native = subprocess.call(["urpmq", "--whatprovides", str(arg)])
    if not native:
        return str(arg)

    print("WARNING: Failed to find a package providing '" + str(arg) + "' dependency\n")
    return ""

# try to find a package that contains given file
def search_file(arg):
    if arg == "":
        return ""

    p = os.popen("urpmf " + str(arg))
    stream = p.readlines()
    if len(stream) > 0:
        return stream[0].split(":")[0]
    else:
        print("WARNING: Failed to find a package providing '" + str(arg) + "' file\n")
        return ""

def funcCMakeLists(currname): # defines all commands from CMakeLists
    # Read mode opens a file for reading only.
    try:
        f = open(currname, "r")
        lines = f.readlines()
    except:
        print("An Error occurred while reading file!")
    finally:
        f.close()

    for line in lines:
        line = line.lower()
        arg = ""
        if ("find_package" in line):
            indexForFirstLoop = line.find('(')
            indexForSpace = line.find(' ')
            indexForSecondLoop = line.find(')')
            if (indexForSpace < indexForSecondLoop and indexForSpace > 0):
                arg = line[indexForFirstLoop + 1 : indexForSpace]
            elif (indexForSpace == -1):
                arg = line[indexForFirstLoop + 1 : indexForSecondLoop]
            # if there is a comma at the end of the arg then delete this comma
            if (len(arg) > 0 and arg[-1] == ','):
                indexForComma = arg.find(',')
                arg = arg[0:indexForComma]
            arg = arg.lower()
            # print(arg)
            provider = search_req(arg)
            if provider:
                requiresCMake.append(provider)

        if ("find_program" in line):
            indexForFirstLoop = line.find('(')
            indexForSpace = line.find(' ')
            indexForSecondLoop = line.find(')')
            if (indexForSpace < indexForSecondLoop and indexForSpace > 0):
                arg = line[indexForSpace + 1 : indexForSecondLoop]
            elif (indexForSpace == -1):
                arg = line[indexForFirstLoop + 1 : indexForSecondLoop]
            # if there is a comma at the end of the arg then delete this comma
            if (len(arg) > 0 and arg[-1] == ','):
                indexForComma = arg.find(',')
                arg = arg[0:indexForComma]
            arg = arg.lower()
            print(arg)
            provider = search_file("bin/" + str(arg) + "$")
            if provider:
                requiresCMake.append(provider)

def funcConfigure(currname): # defines all commands from configure
    # Read mode opens a file for reading only.
    try:
        f = open(currname, "r")
        lines = f.readlines()
    except:
        print("An Error occurred while reading file!")
    finally:
        f.close()
    flag = False # in case if second argument is on the next line
    for line in lines:
        arg = ""
        if (flag):
            findFirstCommaNextLine = line.find(',')
            if (findFirstCommaNextLine != -1):
                arg = line[0 : findFirstCommaNextLine]
                arg = arg.lower()
                if (arg != ""):
                    provider = search_file("bin/" + str(arg) + "$")
                    if provider:
                        requiresConfigure.append(provider)
            flag = False
        if ("AC_CHECK_PROG" in line):
            findAC_CHECK_PROG = line.find("AC_CHECK_PROG")
            indexForFirstSpace = line.find(' ', findAC_CHECK_PROG)
            indexForFirstComma = line.find(',', findAC_CHECK_PROG)
            indexForSecondComma = line.find(',', indexForFirstSpace + 1)
            if (indexForFirstSpace < indexForSecondComma):
                arg = line[indexForFirstSpace + 1 : indexForSecondComma]
            elif (indexForFirstSpace != -1 and indexForSecondComma == -1):
                indexForSecondLoop = line.find(')')
                arg = line[indexForFirstSpace + 1 : indexForSecondLoop]
            elif (indexForFirstComma > 0 and indexForSecondComma == -1):
                flag = True
            arg = arg.lower()
            if (arg != ""):
                provider = search_file("bin/" + str(arg) + "$")
                if provider:
                    requiresConfigure.append(provider)

        arg = ""
        if ("AC_CHECK_LIB" in line):
            indexForFirstLoop = line.find('(')
            indexForSpace = line.find(' ', indexForFirstLoop)
            indexForComma = line.find(',', indexForFirstLoop)
            indexForSecondLoop = line.find(')')
            if (indexForComma > 0):
                arg = line[indexForFirstLoop + 1 : indexForComma]
            elif (indexForSpace == -1 and indexForSecondLoop > 0):
                arg = line[indexForFirstLoop + 1 : indexForSecondLoop]
            # if there is a comma at the end of the arg then delete this comma
            if (len(arg) > 0 and arg[-1] == ','):
                indexForComma = arg.find(',')
                arg = arg[0:indexForComma]
            arg = arg.lower()
            commandsConfigureLibArgs.append(arg)
            arg = "lib" + arg + ".so$"
            newCommand = "urpmf " + "'" + str(arg) + "' | grep -v debug | grep -vi uclibc"
            commandsConfigureLIB.append(newCommand)


def createSpec(Name, Version, Summary, License,
               Group, URL, source_tarball, BuildReq,
               isThereCMake, isThereConfigure):
    specFile = Name + ".spec"  # name of the .spec file
    try:
        file = open(specFile, "w", newline='')  # python 3.4.1
        # file = open(specFile, "wb") # python 2.7.5
        file.write("Summary:\t" + str(Summary) + "\n")
        file.write("Name:\t\t" + str(Name) + "\n")
        file.write("Version:\t" + str(Version) + "\n")
        file.write("Release:\t" + "1" + "\n")
        file.write("License:\t" + str(License) + "\n")
        file.write("Group:\t\t" + str(Group) + "\n")
        file.write("Url:\t\t" + str(URL) + "\n")
        file.write("Source0:\t" + os.path.basename(source_tarball) + "\n")
        file.write("\n")
        file.write(BuildReq)
        file.write("\n")
        file.write("%description" + "\n")
        file.write(str(Summary) + "." + "\n")
        file.write("\n")
        file.write("%files" + "\n")
        file.write("%{_bindir}/*" + "\n")
        file.write("%{_mandir}/man*/*" + "\n")
        file.write("%{_datadir/%{" + str(Name) + "}\n")
        file.write("%{_libdir}/*.so.*" + "\n")
        file.write("\n#----------------------------------------------------------------------------\n\n");
        file.write("%prep" + "\n")
        file.write("%setup -q" + "\n")
        file.write("\n")
        file.write("%build" + "\n")
        if (isThereCMake):
            file.write("%cmake" + "\n")
        elif (isThereConfigure):
            file.write("%configure2_5x" + "\n")
        file.write("%make" + "\n")
        file.write("\n")
        file.write("%install" + "\n")
        if (isThereCMake):
            file.write("%makeintstall_std -C build" + "\n")
        elif (isThereConfigure):
            file.write("%makeintstall_std" + "\n")
        file.write("\n")

    except:
        print("Writing .spec file... Something went wrong!")
    finally:
        file.close()

def parse_command_line():
    global source_tarball

    # Work with ArgumentParser
    parser = argparse.ArgumentParser(description='ROSA RPM Spec Generator')

    parser.add_argument('source_tarball',  action='store', help='path to tarball with source code')
    parser.add_argument('-s', '--summary', action='store', help='package Summary')
    parser.add_argument('-l', '--license', action='store', help='package License')
    parser.add_argument('-g', '--group',   action='store', help='package Group')
    parser.add_argument('-u', '--url',     action='store', help='package Url')

    command_line = parser.parse_args(sys.argv[1:])

    if command_line.summary:
        Summary = command_line.summary
    if command_line.license:
        License = command_line.license
    if command_line.group:
        Group = command_line.group
    if command_line.url:
        URL = command_line.url
    source_tarball = command_line.source_tarball

# Scan all files in a given directory and invoke appropriate analyzer for recignized files
def walk(dir):
    for name in os.listdir(dir):
        currname = os.path.join(dir, name)
        if os.path.islink(currname):
            continue
        if os.path.isfile(currname):
            if (name == "CMakeLists.txt" or name.endswith(".cmake")):
                funcCMakeLists(currname)
            if (name == "configure.ac" or name == "configure.in"):
                funcConfigure(currname)
        else:
            walk(currname)

def check_python(source_path):
    # if there is only one directory in the archive then search there for a setup.py
    # otherwise search in the root of the archive
    if (len(os.listdir(source_path)) == 1):
        os.chdir(os.listdir(source_path)[0])
        isHereSetup = os.path.exists("setup.py")
        if (isHereSetup):
            os.system("python setup.py build bdist_rpm5")
        os.chdir('..')
    else:
        isHereSetup = os.path.exists("setup.py")
        if (isHereSetup):
            os.system("python setup.py build bdist_rpm5")

    return isHereSetup

#
# Main part
#

if __name__ == '__main__':
    parse_command_line()

    # Create temp folder and extract source tarball to it
    tempdir = tempfile.mkdtemp()

    try:
        # formatType:
        # 1 - zip
        # 2 - tar.gz
        # 3 - tar.bz2
        # 4 - tar.xz
        formatType = defineFormat(source_tarball)
        Name, Version = defineNameAndVersion(source_tarball, formatType)
        print("Name: %s \nVersion: %s" %(Name, Version))
        print("Summary: " + str(Summary))
        print("License: " + str(License))
        print("Group: " + str(Group))
        print("URL: " + str(URL))
        openArchiveFile(source_tarball, tempdir)
    except:
        print("Problem with opening '" + source_tarball + "' file")
        exit(1)

    # Save cwd and go to the temp dir where tarball is extracted
    curdir = os.getcwd()
    os.chdir(tempdir)

    # Look for 'setup.py' file at the top dir of archive.
    # If it is found, launch "python setup.py bdis_rpm5" and exit
    if check_python(tempdir):
        print("SPEC GENERATOR: setup.py file was found, launched bdist_rpm5")
        os.chdir(curdir)
        os.system("find " + tempdir + " -type f -name '*.spec' -exec cp {} . \;")
        shutil.rmtree(tempdir)
        exit(0)

    # Collect names of all files inside the archive
    # If configure.*, CMakeFile or other supported files are found,
    # they will be analyze to extract build requirements
    walk(tempdir)

    # For safety, explicitely switch back to the working folder
    os.chdir(curdir)

    BuildReq = ""
    isThereCMake = False
    isThereConfigure = False

    for command in requiresCMake:
        BuildReq += "BuildRequires:\t" + command + "\n"
        isThereCMake = True

    for command in requiresConfigure:
        BuildReq += "BuildRequires:\t" + str(command) + "\n"
        isThereConfigue = True

    if isThereCMake:
        BuildReq += "BuildRequires:\tcmake\n"

    i = 0
    processedCommands = {}
    for command in commandsConfigureLIB:
        if command in processedCommands:
            continue
        processedCommands[command] = 1

        arg = commandsConfigureLibArgs[i]
        p = os.popen(command)
        stream = p.readlines()
        if (len(stream) > 0):
            findColon = stream[0].find(':')
            firstLine = stream[0]
            provide = firstLine[0 : findColon]
            # check for provides
            providesCommand = "urpmq --provides " + provide
            p2 = os.popen(providesCommand)
            output = p2.readlines()
            # work with output
            editedOutput = []
            for line in output:
                findFirstSquareLoop = line.find('[')
                findN = line.find('\n')
                if (findFirstSquareLoop > 0):
                    newLine = line[0 : findFirstSquareLoop]
                else:
                    newLine = line[0 : findN]
                editedOutput.append(newLine)
            # work with edited output
            pkgconfig = []
            req = ""
            for line in editedOutput:
                if (line.find("pkgconfig") > -1):
                    pkgconfig.append(line)
                elif (line.find("glibc") > -1):
                    # glibc is not split into per-library subpackages,
                    # and we can confuse it with uclibc
                    pkgconfig.append(line)
                else:
                    findWordLib = line.find("lib")
                    findWordDevel = line.find("-devel")
                    if (findWordLib == -1 and findWordDevel > 0):
                        req = "BuildRequires:\t" + line + "\n"
                    elif (findWordLib > 0 and findWordDevel > 0 and findWordLib < findWordDevel):
                        req = "BuildRequires:\t" + line + "\n"

            # Overwrite req if there is "pkgconfig":
            for config in pkgconfig:
                if (config.find(arg) > 0):
                    req = "BuildRequires:\t" + config + "\n"
                else:
                    req = "BuildRequires:\t" + config + "\n"
            BuildReq += req
            isThereConfigure = True
        i += 1

    print("The following BuildRequires were detected automatically:\n")
    print(BuildReq)
    createSpec(Name, Version, Summary, License, Group, URL, source_tarball, BuildReq, isThereCMake, isThereConfigure)
    shutil.rmtree(tempdir)
