# Router Architecture Analysis & Proposal

## Current State Analysis
The current router generation logic in `scripts/templates/router.py.j2` introduces hardcoded dependencies on the `backend` service:
```python
from services.backend.src.core.db import get_db
from services.backend.src.controllers.users import UsersController
```
This creates a **circular dependency** (Shared -> Backend -> Shared) and violates the microservice architecture principles, as the "Shared" code is effectively coupled to a specific implementation (the Backend).

## Critique of Proposed Options

### Option 1: Monolith REST (Status Quo-ish)
*   **Pros**: Simplicity. One source of truth for DB access.
*   **Cons**: Extremely rigid. It forces all REST interaction to go through the `backend` service. If you want to spin up a separate microservice with its own API (e.g., for performance or isolation), you can't reuse the generated routers. It defeats the purpose of a "spec-first microservice framework".

### Option 2: Abstract/Repository Pattern
*   **Pros**: High flexibility and decoupling. The generated code becomes truly "shared" and agnostic of the runtime environment.
*   **Cons**: Slightly more setup code is required to wire things up (Dependency Injection).
*   **Verdict**: This is the correct architectural path. The "cons" are minimal and can be handled by the framework.

### Option 3: High-level Spec (Protocol Agnostic)
*   **Pros**: Ultimate flexibility.
*   **Cons**: High complexity. Implementing a generator that supports REST, gRPC, and Queues seamlessly is a large undertaking.
*   **Verdict**: A great long-term vision, but we need a solid decoupled foundation (Option 2) first before we can build this abstraction layer.

## Proposed Solution: The "Router Factory" Pattern

I propose a refined version of **Option 2**. We should utilize a **Dependency Injection (DI)** approach where the generated routers are "factories" that accept their dependencies as arguments.

### How it works

1.  **Generated Router (`shared`)**:
    The `create_router` function will accept `controller_dependency` and `db_dependency` as arguments. It will *not* import anything from `services.backend`.

    **New `router.py.j2` (Concept):**
    ```python
    from typing import Callable
    from fastapi import APIRouter, Depends
    from sqlalchemy.orm import Session
    from shared.generated.protocols import UsersControllerProtocol

    def create_router(
        get_db: Callable[[], Session],
        get_controller: Callable[[], UsersControllerProtocol]
    ) -> APIRouter:
        router = APIRouter(...)

        @router.get("/")
        def get_users(
            session: Session = Depends(get_db),
            controller: UsersControllerProtocol = Depends(get_controller)
        ):
            return controller.get_users(session=session)
        
        return router
    ```

2.  **Service Implementation (`backend`)**:
    The backend service (or any service) is responsible for providing the concrete implementations.

    **`services/backend/src/app/api/router.py`:**
    ```python
    from services.backend.src.core.db import get_db
    from services.backend.src.controllers.users import UsersController
    from shared.generated.routers.users import create_router as create_users_router

    def get_users_controller_impl():
        return UsersController()

    # Inject dependencies at composition time
    users_router = create_users_router(
        get_db=get_db,
        get_controller=get_users_controller_impl
    )
    
    api_router.include_router(users_router)
    ```

### Benefits
1.  **True Decoupling**: `shared` no longer depends on `backend`.
2.  **Reusability**: Any service can mount these routers by providing its own DB session or Controller implementation (even a mock one).
3.  **Testability**: You can easily test the routers by passing mock dependencies, without needing a real database connection or complex patching.
4.  **Flexibility**: Supports the "Option 3" future. If we want to switch to gRPC, the Controller Protocol remains the same, only the transport layer changes.

### Next Steps
1.  Modify `scripts/templates/router.py.j2` to accept dependencies.
2.  Update `services/backend/src/app/api/router.py` to inject the dependencies.
3.  Regenerate code.
