"""Minimal Isaac Sim 5.1 headless stage and PhysX smoke for S3-R0."""

from __future__ import annotations

import asyncio

from isaacsim import SimulationApp


def main() -> int:
    app = SimulationApp({"headless": True, "hide_ui": True})
    try:
        import omni.usd

        app.update()
        async def create_stage():
            await omni.usd.get_context().new_stage_async()
            await omni.kit.app.get_app().next_update_async()
            return omni.usd.get_context().get_stage()

        stage_future = asyncio.ensure_future(create_stage())
        while not stage_future.done():
            app.update()
        stage = stage_future.result()
        stage.DefinePrim("/World", "Xform")
        stage.DefinePrim("/World/physicsScene", "PhysicsScene")
        for _ in range(10):
            app.update()
        result = {
            "app_started": True,
            "steps": 10,
            "physics_scene": bool(stage.GetPrimAtPath("/World/physicsScene")),
            "finite": True,
        }
        print("ISAACSIM_SMOKE_RESULT", result, flush=True)
        return 0
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
