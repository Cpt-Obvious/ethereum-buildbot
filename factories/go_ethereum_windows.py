#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: caktux
# @Date:   2015-04-20 22:03:29
# @Last Modified by:   caktux
# @Last Modified time: 2015-04-24 03:00:29

import factory
reload(factory)
from factory import *

import go_ethereum
reload(go_ethereum)
from go_ethereum import get_short_revision_go

def _go_cmds_win(branch='master'):
    cmds = [
        "mkdir %GOPATH%\\src\\github.com\\ethereum",
        "xcopy /S/E *.* %GOPATH%\\src\\github.com\\ethereum\\go-ethereum\\"
    ]

    return " && ".join(cmds)

def windows_go_factory(branch='develop', isPullRequest=False, headless=True):
    factory = BuildFactory()

    env = {
        "GOPATH": Interpolate("%(prop:workdir)s\\go;%(prop:workdir)s\\build\\Godeps\\_workspace"),
        "PKG_CONFIG_PATH": "C:\Qt\5.4\mingw491_32\lib\pkgconfig",
        "CGO_CPPFLAGS": "-IC:\Qt\5.4\mingw491_32\include\QtCore",
        "LD_LIBRARY_PATH": "C:\Qt\5.4\mingw491_32\lib",
        'PATH': [Interpolate("%(prop:workdir)s\\go\\bin"), "${PATH}"]
    }

    sed = '"C:\\Program Files (x86)\\GnuWin32\\bin\\sed.exe"'

    for step in [
        Git(
            haltOnFailure = True,
            logEnviron = False,
            repourl='https://github.com/ethereum/go-ethereum.git',
            branch=branch,
            mode='full',
            method='copy',
            codebase='go-ethereum',
            retry=(5, 3)
        ),
        Git(
            haltOnFailure = True,
            logEnviron = False,
            repourl = 'https://github.com/ethereum/go-build.git',
            branch = 'master',
            mode = 'incremental',
            codebase = 'go-build',
            retry=(5, 3),
            workdir = 'go-build-%s' % branch
        ),
        SetPropertyFromCommand(
            haltOnFailure = True,
            logEnviron = False,
            name = "set-protocol",
            command = '%s -ne "s/.*ProtocolVersion    = \(.*\)/\\1/p" eth\protocol.go' % sed,
            property = "protocol"
        ),
        SetPropertyFromCommand(
            haltOnFailure = True,
            logEnviron = False,
            name = "update-p2p",
            command = '%s -ne "s/.*baseProtocolVersion.*= \(.*\)/\\1/p" p2p\peer.go' % sed,
            property="p2p"
        ),
        SetPropertyFromCommand(
            haltOnFailure = True,
            logEnviron = False,
            name = "set-version",
            command = '%s -ne "s/.*Version.*=\s*[^0-9]\([0-9]*\.[0-9]*\.[0-9]*\).*/\\1/p" cmd\geth\main.go' % sed,
            property = "version"
        ),
        ShellCommand(
            haltOnFailure = True,
            logEnviron = False,
            name="go-cleanup",
            command=Interpolate("rd /s /q %(prop:workdir)s\\go && mkdir %(prop:workdir)s\\go"),
            description="cleaning up",
            descriptionDone="clean up"
        ),
        ShellCommand(
            haltOnFailure = True,
            logEnviron = False,
            name = "move-src",
            description="moving src",
            descriptionDone="move src",
            command=_go_cmds_win(branch=branch),
            env={"GOPATH": Interpolate("%(prop:workdir)s\go")}
        ),
        ShellCommand(
            haltOnFailure = True,
            logEnviron = False,
            name="install-geth",
            description="installing geth",
            descriptionDone="install geth",
            command="go install -v github.com\ethereum\go-ethereum\cmd\geth",
            env=env
        )
    ]: factory.addStep(step)

    if not headless:
        for step in [
            ShellCommand(
                haltOnFailure = True,
                logEnviron = False,
                name="install-mist",
                description="installing mist",
                descriptionDone="install mist",
                command="go install -v github.com\ethereum\go-ethereum\cmd\mist",
                env=env
            )
        ]: factory.addStep(step)

    for step in [
        ShellCommand(
            flunkOnFailure=False,
            warnOnFailure=True,
            logEnviron=False,
            name="go-test",
            description="go testing",
            descriptionDone="go test",
            command="go test github.com\ethereum\go-ethereum\...",
            decodeRC={0:SUCCESS, -1:WARNINGS, 1:WARNINGS, 2:WARNINGS},
            env=env,
            maxTime=900
        )
    ]: factory.addStep(step)

    if not isPullRequest:
        for step in [
            ShellCommand(
                haltOnFailure = True,
                logEnviron = False,
                name = "pack",
                description = 'pack',
                descriptionDone= 'packed',
                command = ['7z', 'a', 'geth.7z', Interpolate('%(prop:workdir)s\\go\\bin\\geth.exe')]
            ),
            SetProperty(
                description="setting filename",
                descriptionDone="set filename",
                name="set-filename",
                property="filename",
                value=Interpolate("Geth-Win64-%(kw:time_string)s-%(prop:version)s-%(prop:protocol)s-%(kw:short_revision)s.7z", time_string=get_time_string, short_revision=get_short_revision_go)
            ),
            FileUpload(
                haltOnFailure = True,
                name = 'upload',
                slavesrc="geth.7z",
                masterdest = Interpolate("public_html/builds/%(prop:buildername)s/%(prop:filename)s"),
                url = Interpolate("/builds/%(prop:buildername)s/%(prop:filename)s")
            ),
            MasterShellCommand(
                name = "clean-latest-link",
                description = 'cleaning latest link',
                descriptionDone= 'clean latest link',
                command = ['rm', '-f', Interpolate("public_html/builds/%(prop:buildername)s/Geth-Win64-latest.7z")]
            ),
            MasterShellCommand(
                haltOnFailure = True,
                name = "link-latest",
                description = 'linking latest',
                descriptionDone= 'link latest',
                command = ['ln', '-sf', Interpolate("%(prop:filename)s"), Interpolate("public_html/builds/%(prop:buildername)s/Geth-Win64-latest.7z")]
            )
        ]: factory.addStep(step)

    if not isPullRequest and not headless:
        for step in [
            ShellCommand(
                haltOnFailure = True,
                logEnviron = False,
                name = "go-build",
                description = 'go build',
                descriptionDone = 'go build',
                command = ['build.bat'],
                workdir = 'go-build-%s\windows' % branch,
                decodeRC = {0:SUCCESS,1:WARNINGS,2:WARNINGS},
                env={"GOPATH": Interpolate("%(prop:workdir)s\\go")}
            ),
            SetPropertyFromCommand(
                haltOnFailure = True,
                logEnviron = False,
                name = "set-sha1sum",
                command = Interpolate('sha1sum %(prop:workdir)s\\go\\pkg\\ethereum\\mist.exe | grep -o -w "\w\{40\}"'),
                property = 'sha1sum'
            ),
            SetProperty(
                description="setting filename",
                descriptionDone="set filename",
                name="set-filename",
                property="filename",
                value=Interpolate("Mist-Windows-%(kw:time_string)s-%(prop:version)s-%(prop:protocol)s-%(kw:short_revision)s.exe", time_string=get_time_string, short_revision=get_short_revision_go)
            ),
            FileUpload(
                haltOnFailure = True,
                name = 'upload-mist',
                slavesrc=Interpolate("%(prop:workdir)s\\go\\pkg\\ethereum\\mist.exe"),
                masterdest = Interpolate("public_html/builds/%(prop:buildername)s/%(prop:filename)s"),
                url = Interpolate("/builds/%(prop:buildername)s/%(prop:filename)s")
            ),
            MasterShellCommand(
                name = "clean-latest-link",
                description = 'cleaning latest link',
                descriptionDone= 'clean latest link',
                command = ['rm', '-f', Interpolate("public_html/builds/%(prop:buildername)s/Mist-Windows-latest.exe")]
            ),
            MasterShellCommand(
                haltOnFailure = True,
                name = "link-latest",
                description = 'linking latest',
                descriptionDone= 'link latest',
                command = ['ln', '-sf', Interpolate("%(prop:filename)s"), Interpolate("public_html/builds/%(prop:buildername)s/Mist-Windows-latest.exe")]
            )
        ]: factory.addStep(step)

    return factory
