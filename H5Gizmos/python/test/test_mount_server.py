
# Requires python 3.8
# Run from setup folder:
# nosetests --with-coverage --cover-html --cover-package=H5Gizmos --cover-erase --cover-inclusive

import unittest

import numpy as np
import asyncio
import json

from H5Gizmos.python.mount_server import (
    basicTestContext,
    DEFAULT_PORT,
)

from H5Gizmos.python.H5Gizmos import (
    Gizmo, 
    GZ,
    GizmoLiteral,
    JavascriptEvalException,
    NoSuchCallback,
    GizmoLink,
    GizmoReference,
    CantConvertValue,
    NoRequestForOid,
    BadResponseFormat,
    GizmoPacker,
    FINISHED_UNICODE,
    CONTINUE_UNICODE,
    BadMessageIndicator,
    JsonCodec,
    GZPipeline,
    schedule_task,
    TooManyRequests,
)

class TestSleep(unittest.IsolatedAsyncioTestCase):

    async def test_sleep(self, delay=0.1):
        await asyncio.sleep(delay)

class TestStartStop(unittest.IsolatedAsyncioTestCase):

    async def startup(self, context, delay):
        task = context.run_in_task()
        await asyncio.sleep(delay)
        return task

    async def shutdown(self, context, task):
        context.server.finalize()
        await context.shutdown()
        #task2 = schedule_task(shutdown())
        #await task2
        await task
        assert context.server.stopped == True

    async def test_start_stop(self, delay=0.1):
        context = basicTestContext()
        task = await self.startup(context, delay)
        await self.shutdown(context, task)

    async def xtest_start_stop(self, delay=0.1):
        context = basicTestContext()
        task = context.run_in_task()
        await asyncio.sleep(delay)
        context.server.finalize()
        await context.shutdown()
        #task2 = schedule_task(shutdown())
        #await task2
        await task
        assert context.server.stopped == True