

def testAnonCredPluginInstallation(steward):
    assert steward.id is not None
    assert steward.attributeRepo is None
