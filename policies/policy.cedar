// FR-007 — patient self-scope; clinicians tenant-scoped via stored interaction context.

// Allow patients to list and create chat interactions and messages for their own catalog scope.
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

// Allow clinicians to list and create chat interactions and messages within their tenant.
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

// Allow the care-episode service to create patient-scoped interactions on behalf of enrolled patients.
permit (
    principal is chat::Service,
    action == Action::"interaction:create",
    resource
) when {
    resource is chat::ChatCatalog &&
    resource has userUuid &&
    principal.tokenType == "service" &&
    principal.serviceSlug == "care-episode"
};
