from zope.component import getAdapters, queryUtility
from DateTime import DateTime

from Products.CMFCore.utils import getToolByName

from collective.subscribe.interfaces import ISubscriptionCatalog, IUIDStrategy

from .interfaces import IDigestStorage, IDigestAction, IDigestFilterRule
from zope.component._api import getUtilitiesFor


class DigestUtility(object):

    def store_activity(self, folder, activity_key, **info):
        """Gets activity info on a folder and saves it in activity storages
        """
        if 'date' not in info:
            info['date'] = DateTime()

        if 'actor' not in info:
            user = getToolByName(folder, 'portal_membership').getAuthenticatedMember()
            info['actor'] = user.getId()

        site = getToolByName(folder, 'portal_url').getPortalObject()
        catalog = queryUtility(ISubscriptionCatalog)
        storages = getAdapters((site,), IDigestStorage)
        uid = IUIDStrategy(folder)()
        for key, storage in storages:
            subscribers = catalog.search({'%s-digest' % key: uid})
            for k, v in subscribers:
                storage.store_activity(v, activity_key, info)

    def check_digests_to_purge_and_apply(self, site):
        """Check for each storage if it has to be purged and applied, and apply
        """
        storages = getAdapters((site,), IDigestStorage)
        for key, storage in storages:
            if storage.purge_now():
                digest_info = storage.pop()
                self._apply_digest(site, digest_info)

    def _apply_digest(self, site, digest_info):
        """Filter digest info using registered filters
           apply registered strategies for user with filtered info
        """
        filter_rules = [r for n, r in getUtilitiesFor(IDigestFilterRule)]
        digest_strategies =  [r for n, r in getUtilitiesFor(IDigestAction)]

        for userid, info in digest_info.items():
            for rule in filter_rules:
                info = rule(info)

            for action in digest_strategies:
                action(site, userid, info)

    def switch_subscription(self, subscriber, folder, storage_key):
        catalog = queryUtility(ISubscriptionCatalog)
        uid = IUIDStrategy(folder)()
        site = getToolByName(folder, 'portal_url').getPortalObject()
        storages = getAdapters((site,), IDigestStorage)
        for name, storage in storages:
            key = "%s-digest" % name
            if key == storage_key:
                catalog.index(subscriber, uid, key)
            else:
                catalog.unindex(subscriber, uid, key)
