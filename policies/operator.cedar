permit (
    principal is chat::User,
    action,
    resource
) when {
    principal.actors.contains("operator")
};
