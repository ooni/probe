from twisted.scripts import twistd
from twisted.python import usage

from ooni.agent.agent import AgentService

class StartOoniprobeAgentPlugin:
    tapname = "ooniprobe"

    def makeService(self, so):
        return AgentService()

class OoniprobeTwistdConfig(twistd.ServerOptions):
    subCommands = [
        ("StartOoniprobeAgent", None, usage.Options, "ooniprobe agent")
    ]

def run():
    twistd_args = ["--nodaemon"]
    twistd_config = OoniprobeTwistdConfig()
    twistd_args.append("StartOoniprobeAgent")
    try:
        twistd_config.parseOptions(twistd_args)
    except usage.error, ue:
        print("ooniprobe: usage error from twistd: {}\n".format(ue))
    twistd_config.loadedPlugins = {
        "StartOoniprobeAgent": StartOoniprobeAgentPlugin()
    }
    twistd.runApp(twistd_config)
    return 0

if __name__ == "__main__":
    run()
