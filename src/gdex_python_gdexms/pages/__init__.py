"""Table pages, one module per rda-pg-config PHP page; PAGES maps the page name to its class."""

from .dsarch_backupfile import DsarchBackupfile
from .dsarch_dataset import Dataset
from .dsarch_group import DsarchGroup
from .dsarch_helpfile import DsarchHelpfile
from .dsarch_savedfile import DsarchSavedfile
from .dsarch_taccfile import DsarchTaccfile
from .dsarch_version import DsarchVersion
from .dsarch_webfile import DsarchWebfile
from .dscheck_check import DscheckCheck
from .dscheck_daemon import DscheckDaemon
from .dscheck_history import DscheckHistory
from .dscheck_hostname import DscheckHostname
from .dsrqst_control import DsrqstControl
from .dsrqst_dslimit import DsrqstDslimit
from .dsrqst_file import DsrqstFile
from .dsrqst_partition import DsrqstPartition
from .dsrqst_purge import DsrqstPurge
from .dsrqst_request import DsrqstRequest
from .dsrqst_tarfile import DsrqstTarfile
from .dsrqst_userlimit import DsrqstUserlimit
from .dsupdt_control import DsupdtControl
from .dsupdt_localfile import DsupdtLocalfile
from .dsupdt_remotefile import DsupdtRemotefile
from .rdadb_ncar_user import MSSUser
from .rdadb_org_type import OrgType
from .rdadb_public_user import WebUser
from .rdadb_specialist import DssSpecialist

PAGES = {
   'rdadb_specialist': DssSpecialist,
   'rdadb_org_type': OrgType,
   'rdadb_ncar_user': MSSUser,
   'rdadb_public_user': WebUser,
   'dsarch_dataset': Dataset,
   'dsarch_group': DsarchGroup,
   'dsarch_savedfile': DsarchSavedfile,
   'dsarch_backupfile': DsarchBackupfile,
   'dsarch_webfile': DsarchWebfile,
   'dsarch_helpfile': DsarchHelpfile,
   'dsarch_version': DsarchVersion,
   'dsarch_taccfile': DsarchTaccfile,
   'dsupdt_control': DsupdtControl,
   'dsupdt_localfile': DsupdtLocalfile,
   'dsupdt_remotefile': DsupdtRemotefile,
   'dsrqst_control': DsrqstControl,
   'dsrqst_request': DsrqstRequest,
   'dsrqst_partition': DsrqstPartition,
   'dsrqst_dslimit': DsrqstDslimit,
   'dsrqst_userlimit': DsrqstUserlimit,
   'dsrqst_file': DsrqstFile,
   'dsrqst_tarfile': DsrqstTarfile,
   'dsrqst_purge': DsrqstPurge,
   'dscheck_hostname': DscheckHostname,
   'dscheck_daemon': DscheckDaemon,
   'dscheck_check': DscheckCheck,
   'dscheck_history': DscheckHistory,
}
