{{- define "prepforge.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "prepforge.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "prepforge.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "prepforge.labels" -}}
app.kubernetes.io/name: {{ include "prepforge.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "prepforge.selectorLabels" -}}
app.kubernetes.io/name: {{ include "prepforge.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "prepforge.image" -}}
{{- printf "%s:%s" .Values.image.repository .Values.image.tag -}}
{{- end -}}
