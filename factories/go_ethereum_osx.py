#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: caktux
# @Date:   2015-02-23 15:02:55
# @Last Modified by:   caktux
# @Last Modified time: 2015-03-09 17:49:56

import factory
reload(factory)
from factory import *

import go_ethereum
reload(go_ethereum)
from go_ethereum import get_short_revision_go, _go_cmds


def osx_go_factory(branch='develop', isPullRequest=False, headless=True):
    factory = BuildFactory()

    env = {
        "GOPATH": Interpolate("%(prop:workdir)s/go:%(prop:workdir)s/build/Godeps/_workspace"),
        "PKG_CONFIG_PATH": "/usr/local/opt/qt5/lib/pkgconfig",
        "CGO_CPPFLAGS": "-I/usr/local/opt/qt5/include/QtCore",
        "LD_LIBRARY_PATH": "/usr/local/opt/qt5/lib",
        'PATH': [Interpolate("%(prop:workdir)s/go/bin"), "${PATH}"]
    }

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
            name = "update-protocol",
            command = 'sed -ne "s/.*ProtocolVersion    = \(.*\)/\\1/p" eth/protocol.go',
            property = "protocol"
        ),
        SetPropertyFromCommand(
            haltOnFailure = True,
            logEnviron = False,
            name = "update-p2p",
            command = 'sed -ne "s/.*baseProtocolVersion.*= \(.*\)/\\1/p" p2p/protocol.go',
            property = "p2p"
        ),
        SetPropertyFromCommand(
            haltOnFailure = True,
            logEnviron = False,
            name = "update-version",
            command = 'sed -ne "s/.*Version.*= \\"\(.*\)\\"/\\1/p" cmd/ethereum/main.go',
            property = "version"
        ),
        ShellCommand(
            haltOnFailure = True,
            logEnviron = False,
            name="go-cleanup",
            command=Interpolate("rm -rf %(prop:workdir)s/go"),
            description="cleaning up",
            descriptionDone="clean up",
            env={"GOPATH": Interpolate("%(prop:workdir)s/go")}
        ),
        ShellCommand(
            haltOnFailure = True,
            logEnviron = False,
            name = "move-src",
            description="moving src",
            descriptionDone="move src",
            command=_go_cmds(branch=branch),
            env={"GOPATH": Interpolate("%(prop:workdir)s/go")}
        ),
        ShellCommand(
            haltOnFailure = True,
            logEnviron = False,
            name="install-ethereum",
            description="installing ethereum",
            descriptionDone="install ethereum",
            command="go install -v github.com/ethereum/go-ethereum/cmd/ethereum",
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
                command="go install -v github.com/ethereum/go-ethereum/cmd/mist",
                env=env
            )
        ]: factory.addStep(step)

    if not isPullRequest and headless:
        for step in [
            Trigger(
                schedulerNames=["go-ethereum-%s-brew" % branch],
                waitForFinish=False,
                set_properties={
                    "p2p": Interpolate("%(prop:p2p)s"),
                    "protocol": Interpolate("%(prop:protocol)s"),
                    "version": Interpolate("%(prop:version)s")
                }
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
                command = ['python', 'build.py'],
                workdir = 'go-build-%s/osx' % branch,
                decodeRC = {0:SUCCESS,1:WARNINGS,2:WARNINGS},
                env={"GOPATH": Interpolate("%(prop:workdir)s/go")}
            ),
            SetPropertyFromCommand(
                haltOnFailure = True,
                logEnviron = False,
                name = "set-sha1sum",
                command = Interpolate('sha1sum osx/Mist.dmg | grep -o -w "\w\{40\}"'),
                property = 'sha1sum',
                workdir = 'go-build-%s' % branch
            ),
            SetProperty(
                description="setting filename",
                descriptionDone="set filename",
                name="set-filename",
                property="filename",
                value=Interpolate("Mist-OSX-%(kw:time_string)s-%(prop:version)s-%(prop:protocol)s-%(kw:short_revision)s.dmg", time_string=get_time_string, short_revision=get_short_revision_go)
            ),
            FileUpload(
                haltOnFailure = True,
                name = 'upload-mist',
                slavesrc="osx/Mist.dmg",
                masterdest = Interpolate("public_html/builds/%(prop:buildername)s/%(prop:filename)s"),
                url = Interpolate("/builds/%(prop:buildername)s/%(prop:filename)s"),
                workdir = 'go-build-%s' % branch
            ),
            MasterShellCommand(
                name = "clean-latest-link",
                description = 'cleaning latest link',
                descriptionDone= 'clean latest link',
                command = ['rm', '-f', Interpolate("public_html/builds/%(prop:buildername)s/Mist-OSX-latest.dmg")]
            ),
            MasterShellCommand(
                haltOnFailure = True,
                name = "link-latest",
                description = 'linking latest',
                descriptionDone= 'link latest',
                command = ['ln', '-sf', Interpolate("%(prop:filename)s"), Interpolate("public_html/builds/%(prop:buildername)s/Mist-OSX-latest.dmg")]
            )
        ]: factory.addStep(step)

    return factory

