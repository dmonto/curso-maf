# ============================================================
# Asignación de permisos de laboratorio MAF
# Azure AI Search + Storage Blob para todos los usuarios/grupos
# con acceso directo al Resource Group
# ============================================================

$ErrorActionPreference = "Stop"

# Ajustar si cambia el entorno
$SUBSCRIPTION_ID = "1024087b-9941-49d0-b512-5e0a9f7e8e7a"
$RESOURCE_GROUP  = "microsoft-agent-framework-course"
$SEARCH_SERVICE  = "cursoiasearchasteci"
$STORAGE_ACCOUNT = "cursoiastorageasteci"

# Roles necesarios para Azure AI Search
$SEARCH_ROLES = @(
    "Search Service Contributor",
    "Search Index Data Contributor",
    "Search Index Data Reader"
)

# Roles necesarios para Blob Storage
$STORAGE_ROLES = @(
    "Storage Blob Data Reader",
    "Storage Blob Data Contributor"
)

Write-Host "Usando suscripción $SUBSCRIPTION_ID..." -ForegroundColor Cyan
az account set --subscription $SUBSCRIPTION_ID

$rgScope = "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"

$searchScope = "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Search/searchServices/$SEARCH_SERVICE"

$storageScope = "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"

Write-Host "`nLeyendo asignaciones directas del Resource Group..." -ForegroundColor Cyan

$assignmentsJson = az role assignment list `
    --scope $rgScope `
    --query "[].{principalId:principalId, principalName:principalName, principalType:principalType, role:roleDefinitionName}" `
    -o json

$assignments = $assignmentsJson | ConvertFrom-Json

if (-not $assignments) {
    throw "No se encontraron asignaciones directas en el Resource Group $RESOURCE_GROUP."
}

# Nos quedamos con usuarios y grupos. Evitamos ServicePrincipal, ManagedIdentity, etc.
$principals = $assignments |
    Where-Object { $_.principalType -in @("User", "Group") } |
    Sort-Object principalId -Unique

Write-Host "`nPrincipales encontrados:" -ForegroundColor Cyan

$principals |
    Select-Object principalName, principalType, principalId |
    Format-Table -AutoSize

if (-not $principals) {
    throw "No se encontraron usuarios o grupos directos en el Resource Group."
}

function Add-RoleIfMissing {
    param(
        [Parameter(Mandatory = $true)]
        [string] $PrincipalId,

        [Parameter(Mandatory = $true)]
        [string] $PrincipalType,

        [Parameter(Mandatory = $true)]
        [string] $RoleName,

        [Parameter(Mandatory = $true)]
        [string] $Scope
    )

    $existing = az role assignment list `
        --assignee $PrincipalId `
        --scope $Scope `
        --include-inherited `
        --query "[?roleDefinitionName=='$RoleName'] | length(@)" `
        -o tsv

    if ([int]$existing -gt 0) {
        Write-Host "  OK existe: $RoleName" -ForegroundColor DarkGray
        return
    }

    Write-Host "  Asignando: $RoleName" -ForegroundColor Yellow

    az role assignment create `
        --assignee-object-id $PrincipalId `
        --assignee-principal-type $PrincipalType `
        --role $RoleName `
        --scope $Scope `
        -o none
}

foreach ($principal in $principals) {
    Write-Host "`n============================================================"
    Write-Host "Principal: $($principal.principalName) [$($principal.principalType)]"
    Write-Host "ObjectId:  $($principal.principalId)"
    Write-Host "============================================================"

    Write-Host "`nAzure AI Search: $SEARCH_SERVICE" -ForegroundColor Cyan

    foreach ($role in $SEARCH_ROLES) {
        Add-RoleIfMissing `
            -PrincipalId $principal.principalId `
            -PrincipalType $principal.principalType `
            -RoleName $role `
            -Scope $searchScope
    }

    Write-Host "`nStorage Account: $STORAGE_ACCOUNT" -ForegroundColor Cyan

    foreach ($role in $STORAGE_ROLES) {
        Add-RoleIfMissing `
            -PrincipalId $principal.principalId `
            -PrincipalType $principal.principalType `
            -RoleName $role `
            -Scope $storageScope
    }
}

Write-Host "`nPermisos asignados. Puede tardar unos minutos en propagarse RBAC." -ForegroundColor Green