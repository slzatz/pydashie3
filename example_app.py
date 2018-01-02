#from example_samplers import *
from example_samplers_sz import *
from salesforce import SalesforceSampler
from config import port

def run(app, xyzzy):
    samplers = [
        SynergySampler(xyzzy, 3),
        BuzzwordsSampler(xyzzy, 2), # 10
        ConvergenceSampler(xyzzy, 1),
        CalendarSampler(xyzzy, 600),
        IndustrySampler(xyzzy,10),
        TwitterSampler(xyzzy, 300),
        OutlookSampler(xyzzy, 300,)
        SalesforceSampler(xyzzy, 300)
    ]

    try:
        app.run(debug=True,
                port=port,
                threaded=True,
                use_reloader=False,
                use_debugger=True
                )
    finally:
        print("Disconnecting clients")
        xyzzy.stopped = True
        
        print("Stopping %d timers" % len(samplers))
        for (i, sampler) in enumerate(samplers):
            sampler.stop()

    print("Done")
