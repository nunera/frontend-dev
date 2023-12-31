from flask import request, session
from app.controllers.common import json_response
from app.pkgs.prompt.prompt import aiAnalyzeError
from app.pkgs.devops.local_tools import compileCheck, lintCheck
from app.pkgs.tools.i18b import getI18n
from app.pkgs.devops.devops import triggerPipeline, getPipelineStatus
from app.pkgs.knowledge.app_info import getServiceGitPath, getServiceDockerImage
from app.pkgs.tools.file_tool import get_ws_path
from app.pkgs.devops.cd import triggerCD
from app.models.application_service import ApplicationService
from flask import Blueprint
from app.models.setting import getCIConfigList, getCDConfigList
from app.models.requirement import Requirement

bp = Blueprint('step_devops', __name__, url_prefix='/step_devops')

@bp.route('/trigger_ci', methods=['POST'])
@json_response
def trigger_ci():
    serviceName = request.json.get('repo_path')
    username = session['username']
    requirementID = request.json.get('task_id')
    req = Requirement.get_requirement_by_id(requirementID) 
    serviceInfo = ApplicationService.get_service_by_name(req["app_id"], serviceName)
    tenantID = session['tenant_id']
    ciConfigList, success = getCIConfigList(tenantID, req["app_id"])
    branch = session[username]['memory']['task_info']['feature_branch']

    result, piplineID, piplineUrl, success = triggerPipeline(requirementID, branch, serviceInfo, ciConfigList[0])
    if success:
        return {"name": 'ci', "info": {"piplineID": piplineID, "repopath": serviceInfo["git_path"], "piplineUrl": piplineUrl}}
    else:
        raise Exception(result)


@bp.route('/query_ci', methods=['GET'])
@json_response
def plugin_ci():
    pipeline_id = request.args.get('piplineID')
    repopath = request.args.get('repopath')
    tenantID = session['tenant_id']
    requirementID = request.args.get('task_id')
    req = Requirement.get_requirement_by_id(requirementID) 
    ciConfigList, success = getCIConfigList(tenantID, req["app_id"] )

    piplineJobs, success = getPipelineStatus(pipeline_id, repopath, ciConfigList[0])
    print("piplineJobs:", piplineJobs)

    if success:
        return {'piplineJobs': piplineJobs}
    else:
        raise Exception(piplineJobs)
    


@bp.route('/check_compile', methods=['POST'])
@json_response
def check_compile():
    _ = getI18n("controllers")
    requirementID = request.json.get('task_id')
    serviceName = request.json.get('repo_path')
    wsPath = get_ws_path(requirementID)
    req = Requirement.get_requirement_by_id(requirementID)
    gitPath, success = getServiceGitPath(req["app_id"], serviceName)

    success, message = compileCheck(requirementID, wsPath, gitPath)

    if success:
        reasoning = _("Compile check pass.")
        return {'pass': True, 'message': message, 'reasoning': reasoning}
    else:
        reasoning, success = aiAnalyzeError(requirementID, message, "")
        if success:
            return {'pass': False, 'message': message, 'reasoning': reasoning}
        else:
            raise Exception(_("Compile check failed for unknown reasons."))


@bp.route('/check_lint', methods=['POST'])
@json_response
def check_lint():
    _ = getI18n("controllers")
    requirementID = request.json.get('task_id')
    file_path = request.json.get('file_path')
    serviceName = request.json.get('service_name')
    req = Requirement.get_requirement_by_id(requirementID)
    gitPath, success = getServiceGitPath(req["app_id"], serviceName)
    ws_path = get_ws_path(requirementID)

    success, message = lintCheck(requirementID, ws_path, gitPath, file_path)

    if success:
        reasoning = _("Static code scan passed.")
        return {'pass': True, 'message': message, 'reasoning': reasoning}
    else:
        reasoning, success = aiAnalyzeError(requirementID, message, file_path)
        if success:
            return {'pass': False, 'message': message, 'reasoning': reasoning}
        else:
            raise Exception(_("Static code scan failed for unknown reasons."))

@bp.route('/trigger_cd', methods=['POST'])
@json_response
def trigger_cd():
    requirementID = request.json.get('task_id')
    req = Requirement.get_requirement_by_id(requirementID)
    serviceName = request.json.get('repo_path')
    serviceInfo = ApplicationService.get_service_by_name(req["app_id"], serviceName)
    image, success = getServiceDockerImage(req["app_id"], serviceName)
    tenantID = session['tenant_id']
    cdConfigList, success = getCDConfigList(tenantID, req["app_id"])

    result, success = triggerCD(requirementID, image, serviceInfo, cdConfigList[0])
    if success:
        return {"internet_ip": result}
    else:
        raise Exception(result)