"""Table pages, one module per rda-pg-config PHP page; PAGES maps the page name to its class."""

from .dscheck_check import DscheckCheck
from .dsarch_webfile import DsarchWebfile
from .rdadb_org_type import OrgType

PAGES = {
   'rdadb_org_type': OrgType,
   'dsarch_webfile': DsarchWebfile,
   'dscheck_check': DscheckCheck,
}
