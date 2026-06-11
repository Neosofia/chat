// FR-007 — patient self-scope; clinicians tenant-scoped via User Service lookup in entities.

permit (
    principal is chat::User,
    action in [
        Action::"interaction:list",
        Action::"interaction:create",
        Action::"message:list",
        Action::"message:create",
    ],
    resource
) when {
    resource is chat::ChatCatalog &&
    principal.actors.contains("patient") &&
    resource has userUuid &&
    principal.uuid == resource.userUuid
};

permit (
    principal is chat::User,
    action in [
        Action::"interaction:list",
        Action::"interaction:create",
        Action::"message:list",
        Action::"message:create",
    ],
    resource
) when {
    resource is chat::ChatCatalog &&
    principal.actors.contains("clinician") &&
    principal.tenantId == resource.tenantId &&
    principal.tenantId != ""
};
