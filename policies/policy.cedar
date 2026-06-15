// User-scoped interaction and message catalogs mirror REST route layout.

// Patients: own-user interaction catalog and message catalog under an interaction.
permit (
    principal is chat::User,
    action in [
        Action::"interaction:list",
        Action::"interaction:create",
    ],
    resource
) when {
    resource is chat::InteractionCatalog &&
    resource has userUuid &&
    principal.actors.contains("patient") &&
    principal.uuid == resource.userUuid
};

permit (
    principal is chat::User,
    action in [
        Action::"message:list",
        Action::"message:create",
    ],
    resource
) when {
    resource is chat::MessageCatalog &&
    resource has userUuid &&
    principal.actors.contains("patient") &&
    principal.uuid == resource.userUuid
};

// Aggregate last-activity reads use the user interaction catalog scope.
permit (
    principal is chat::User,
    action == Action::"message:list",
    resource
) when {
    resource is chat::InteractionCatalog &&
    resource has userUuid &&
    principal.actors.contains("patient") &&
    principal.uuid == resource.userUuid
};

// Clinicians: same-tenant interaction and message catalogs.
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
    (
        resource is chat::InteractionCatalog ||
        resource is chat::MessageCatalog
    ) &&
    principal.actors.contains("clinician") &&
    resource has tenantId &&
    principal.tenantId == resource.tenantId &&
    principal.tenantId != ""
};

// Care Episode service opens interactions on behalf of enrolled patients.
permit (
    principal is chat::Service,
    action == Action::"interaction:create",
    resource
) when {
    resource is chat::InteractionCatalog &&
    resource has userUuid &&
    principal.tokenType == "service" &&
    principal.serviceSlug == "care-episode"
};
