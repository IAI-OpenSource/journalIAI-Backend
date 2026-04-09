from app.auth.role_checker import RoleChecker, OthersCustomRoleChecker
from app.db.models.enums import UserRole, ExecutiveRoleType


class RoleDepends:

  all_authorize = RoleChecker([
      UserRole.STUDENT,
      UserRole.CLUB_LEADER,
      UserRole.DELEGATE,
      UserRole.MODERATOR,
      UserRole.ADMIN,
      UserRole.SPECTATOR,
      UserRole.EXECUTIVE_MEMBER,
    ])

  only_committee_authorize = RoleChecker([
      ExecutiveRoleType.DELEGUE_GENERAL,
      ExecutiveRoleType.SECRETAIRE_GENERAL_ADJOINT,
      ExecutiveRoleType.SECRETAIRE_GENERAL,
      ExecutiveRoleType.SECRETAIRE_GENERAL_ADJOINT,
      ExecutiveRoleType.CACA,
      ExecutiveRoleType.VICE_CACA,
      ExecutiveRoleType.TRESORIER_GENERAL,
      ExecutiveRoleType.VICE_TRESORIER_GENERAL,
      ExecutiveRoleType.CONSEILLER
    ])

  only_admin_authorize = RoleChecker([
      UserRole.ADMIN,
    ])

  only_club_leader_authorize = RoleChecker([
      UserRole.CLUB_LEADER
    ])

  only_those_can_post_authorize = OthersCustomRoleChecker.only_can_posts
  
  only_managers_authorize = RoleChecker([
      UserRole.MODERATOR,
      UserRole.ADMIN,
    ])
