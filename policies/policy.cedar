permit (
    principal is chat::User,
    action in [Action::"message:create", Action::"message:read"],
    resource
);