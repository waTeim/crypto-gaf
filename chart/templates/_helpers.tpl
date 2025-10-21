{{/*
Chart-wide helpers
*/}}

{{- define "crypto-gaf.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "crypto-gaf.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "crypto-gaf.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "crypto-gaf.selectorLabels" -}}
app.kubernetes.io/name: {{ include "crypto-gaf.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "crypto-gaf.labels" -}}
helm.sh/chart: {{ include "crypto-gaf.chart" . }}
{{ include "crypto-gaf.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Component helpers
*/}}

{{- define "crypto-gaf.componentName" -}}
{{- $root := .root -}}
{{- $component := .component -}}
{{- printf "%s-%s" (include "crypto-gaf.fullname" $root) $component | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "crypto-gaf.componentSelectorLabels" -}}
app.kubernetes.io/name: {{ include "crypto-gaf.componentName" . }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "crypto-gaf.componentLabels" -}}
{{ include "crypto-gaf.labels" .root }}
{{ include "crypto-gaf.componentSelectorLabels" . }}
{{- end }}

{{- define "crypto-gaf.collect.fullname" -}}
{{- include "crypto-gaf.componentName" (dict "root" . "component" "collect") -}}
{{- end }}

{{- define "crypto-gaf.calculate.fullname" -}}
{{- include "crypto-gaf.componentName" (dict "root" . "component" "calculate") -}}
{{- end }}

{{/*
Container image helpers
*/}}

{{- define "crypto-gaf.image" -}}
{{- $root := .root -}}
{{- $component := .component -}}
{{- $global := default (dict "registry" "" "name" "crypto-gaf" "tag" "latest" "pullPolicy" "IfNotPresent") $root.Values.image -}}
{{- $componentValues := default dict (index $root.Values $component) -}}
{{- $componentImage := default dict $componentValues.image -}}
{{- $registry := default $global.registry $componentImage.registry -}}
{{- $name := default $global.name $componentImage.name -}}
{{- $repository := default (printf "%s-%s" $name $component) $componentImage.repository -}}
{{- $tag := default $global.tag $componentImage.tag -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry $repository $tag -}}
{{- else -}}
{{- printf "%s:%s" $repository $tag -}}
{{- end -}}
{{- end }}

{{- define "crypto-gaf.imagePullPolicy" -}}
{{- $root := .root -}}
{{- $component := .component -}}
{{- $global := default (dict "pullPolicy" "IfNotPresent") $root.Values.image -}}
{{- $componentValues := default dict (index $root.Values $component) -}}
{{- $componentImage := default dict $componentValues.image -}}
{{- default $global.pullPolicy $componentImage.pullPolicy -}}
{{- end }}

{{/*
Database helpers (Bitnami PostgreSQL dependency)
*/}}

{{- define "crypto-gaf.postgres.host" -}}
{{- if and .Values.postgresql.primary .Values.postgresql.primary.service .Values.postgresql.primary.service.hostname }}
{{- .Values.postgresql.primary.service.hostname -}}
{{- else }}
{{- printf "%s-postgresql" .Release.Name -}}
{{- end -}}
{{- end }}

{{- define "crypto-gaf.postgres.port" -}}
{{- $port := 5432 -}}
{{- if and .Values.postgresql.primary .Values.postgresql.primary.service .Values.postgresql.primary.service.ports.postgresql }}
  {{- $port = .Values.postgresql.primary.service.ports.postgresql -}}
{{- end -}}
{{- printf "%v" $port -}}
{{- end }}

{{- define "crypto-gaf.postgres.user" -}}
{{- if and .Values.postgresql.auth.username (ne .Values.postgresql.auth.username "") -}}{{- .Values.postgresql.auth.username -}}{{- else -}}postgres{{- end -}}
{{- end }}

{{- define "crypto-gaf.postgres.database" -}}
{{- if and .Values.postgresql.auth.database (ne .Values.postgresql.auth.database "") -}}{{- .Values.postgresql.auth.database -}}{{- else -}}postgres{{- end -}}
{{- end }}

{{- define "crypto-gaf.postgres.secretName" -}}
{{- if and .Values.postgresql.auth.existingSecret (ne .Values.postgresql.auth.existingSecret "") }}
{{- .Values.postgresql.auth.existingSecret -}}
{{- else }}
{{- printf "%s-postgresql" .Release.Name -}}
{{- end -}}
{{- end }}

{{- define "crypto-gaf.postgres.passwordKey" -}}
{{- if and .Values.postgresql.auth.username (ne .Values.postgresql.auth.username "") -}}password{{- else -}}postgres-password{{- end -}}
{{- end }}

{{- define "crypto-gaf.postgres.passwordValue" -}}
{{- $pgUser := include "crypto-gaf.postgres.user" . -}}
{{- if and (eq $pgUser "postgres") (ne (default "" .Values.postgresql.auth.postgresPassword) "") -}}
value: {{ .Values.postgresql.auth.postgresPassword | quote }}
{{- else if and (ne $pgUser "postgres") (ne (default "" .Values.postgresql.auth.password) "") -}}
value: {{ .Values.postgresql.auth.password | quote }}
{{- else -}}
valueFrom:
  secretKeyRef:
    name: {{ include "crypto-gaf.postgres.secretName" . | quote }}
    key: {{ include "crypto-gaf.postgres.passwordKey" . | quote }}
{{- end -}}
{{- end }}
