import xml.dom.minidom
import Tkinter
import tkMessageBox
import tkFileDialog
import tkSimpleDialog
import os
import pickle

# DJO McIntyre Feb 2014
# dom_mcintyre at hotmail.com
# Simple program to convert zone speed targets in a .tcx workout file to custom
# zone paces.
# Future improvements: less running-centric; it only supports one set of zones,
# and only as paces, though those zones will be displayed as speeds rather than
# paces if the sport is not running
# better file save; at the moment it just saves the file in the same directory
# with cz plus whatever number is required to avoid overwriting existing files
# inserted before the .tcx extension
# better default saving - currently it just pickles to wherever the .py file is stored
# this is hostile to multiple users. It does work perfectly for pyinstaller under
# Win and Linux, though.
# permit overlapping zones

# global variables for GUI
rootWin = None
currwd = None
Debug = False

# Stores zones as strings, supplies default values
# defaults are overwritten from ztconfig.cfg at startup if it exists
class ztZones:
    # first ten numbers are zone base, last is top of zone 10
    ZTzones=['59:59',
        '10:00',
        '8:45',
        '7:53',
        '7:24',
        '7:03',
        '6:49',
        '6:25',
        '6:17',
        '5:57',
        '2:40']

    ZTdistunit='m'

    def nzones(self):
        return (len(self.ZTzones)-1)

    def distunit(self):
        return self.ZTdistunit

    def setdistunit(self,newdistunit):
        self.ZTdistunit = newdistunit

    def zones(self):
        return self.ZTzones

    def setzones(self,newzones):
        self.ZTzones = newzones

# instance of class
ztZ = ztZones()

# dialog box to adjust zones
class setZones(tkSimpleDialog.Dialog):
    def body(self,master):
        self.entries=[]
        for zone in range(ztZ.nzones()): # need top of zone 10
            Tkinter.Label(master, text="Bottom of zone "+str(zone+1)).grid(row=zone,sticky='W')
            self.entries.append(Tkinter.Entry(master))
            self.entries[zone].grid(row=zone,column=1,sticky='W')
            self.entries[zone].insert(0,ztZ.zones()[zone])
        Tkinter.Label(master,text="Top of zone "+str(ztZ.nzones())).grid(row=ztZ.nzones(),sticky='W')
        self.entries.append(Tkinter.Entry(master))
        self.entries[ztZ.nzones()].grid(row=ztZ.nzones(),column=1,sticky='W')
        self.entries[ztZ.nzones()].insert(0,ztZ.zones()[ztZ.nzones()])
        Tkinter.Label(master,text='Pace units').grid(row=ztZ.nzones()+1,sticky='W')
        self.stv = Tkinter.StringVar()
        self.stv.set(ztZ.distunit())
        Tkinter.Radiobutton(master,text='Min/mi',variable=self.stv,value='m').grid(
                          row=ztZ.nzones()+1,column=1,sticky='W')
        Tkinter.Radiobutton(master,text='Min/km',variable=self.stv,value='k').grid(
                          row=ztZ.nzones()+1,column=2,sticky='W')

    def validate(self):
        entriesOK = True
        for entry in self.entries:
            try:
                (a,b) = entry.get().split(':')
                test1 = int(a)
                test2 = int(b)
            except:
                entriesOK = False
        if not entriesOK:
            tkMessageBox.showerror('Error setting zones','Zones must be of the form mm:ss')
        return entriesOK

    def apply(self):
        strzones = ['']*(ztZ.nzones()+1)
        if Debug:
            print len(strzones)
        self.result=[]
        for loop in range(ztZ.nzones()+1):
            strzones[loop] = self.entries[loop].get()
            self.result.append(self.entries[loop].get())
        ztZ.setzones(strzones)
        ztZ.setdistunit(self.stv.get())
        # self.result is not used, the hard work is done by ztZ.set... calls
        self.result.append(self.stv.get())


# class definining main program
class zoneTransformApp:
    def __init__(self,myParent):
        global currwd
        # remember parent for later removal
        self.myParent = myParent
        self.myParent.title('Zone Converter')

        # initialise some variables

        currwd = os.getcwd()

        # if possible, check for config file containing user's selected zones
        try:
            self.sourcedir = os.path.dirname(os.path.abspath(__file__))
        except:
            self.sourcedir = None
        if self.sourcedir:
            os.chdir(self.sourcedir)
            if os.path.exists('ztconfig.cfg') and os.path.isfile('ztconfig.cfg'):
                if not self.loadZones():
                    tkMessageBox.showinfo('Default zone load','Load failed. Try deleting ztconfig.cfg in python code directory')
                os.chdir(currwd)
        self.refreshZones()


        # minimal GUI of a few buttons
        nrow = 0
        ncol = 0
        self.buttonRun = Tkinter.Button(myParent)
        self.buttonRun.grid(row=nrow,column=ncol,sticky='WE')
        self.buttonRun['text'] = 'Run'
        self.buttonRun.config(command=self.runCallback)
        ncol=ncol+1
        self.buttonSetZones = Tkinter.Button(myParent)
        self.buttonSetZones.grid(row=nrow,column=ncol,sticky='WE')
        self.buttonSetZones['text'] = 'Set Zones'
        self.buttonSetZones.config(command=self.setZonesCallback)
        ncol=ncol+1
        self.buttonSaveZones = Tkinter.Button(myParent)
        self.buttonSaveZones.grid(row=nrow,column=ncol,sticky='WE')
        self.buttonSaveZones['text'] = 'Save Zones as Default'
        self.buttonSaveZones.config(command=self.saveZonesCallback)
        ncol=ncol+1
        # Not particularly useful, as the default zones are always loaded
        # at startup if the file exists. Create to avoid errors, but
        # don't configure
        self.buttonLoadZones = Tkinter.Button(myParent)
        #self.buttonLoadZones.grid(row=nrow,column=ncol,sticky='WE')
        #self.buttonLoadZones['text'] = 'Load Default Zones'
        #self.buttonLoadZones.config(command=self.loadZonesCallback)
        #ncol=ncol+1

        self.buttonExit = Tkinter.Button(myParent)
        self.buttonExit.grid(row=nrow,column=ncol,sticky='WE')
        self.buttonExit['text'] = 'Exit'
        self.buttonExit.config(command=self.exitCallback)


    def runCallback(self):
        # Core of the program
        # Opens tcx file, parses it as xml, finds any predefined zones and
        # rewrites those nodes as targets with custom zones
        # uses pace for running, speed for bike/other
        # automatically saves edited file if there are any changes
        global currwd
        self.buttonRun.configure(relief='sunken')
        self.fpath = tkFileDialog.askopenfilename()
        (currwd,self.fname) = os.path.split(self.fpath)
        os.chdir(currwd)
        try:
            dom1 = xml.dom.minidom.parse(self.fname)
        except Exception as e:
            tkMessageBox.showerror('zonetransform','Exception '+str(e)+'encountered opening\n'+
                                      'file '+self.fname)
            self.buttonRun.configure(relief='raised')
            return
        modified = False
        for thisnode in dom1.getElementsByTagName('SpeedZone'):
            if thisnode.getAttribute('xsi:type') == u'PredefinedSpeedZone_t':
                modified = True
                if Debug:
                    print 'found a Zone',thisnode.getAttribute('xsi:type')
                foundVal = False
                for subnode in thisnode.childNodes:
                    if subnode.nodeName == 'Number':
                        for ssn in subnode.childNodes:
                            if ssn.nodeName == '#text':
                                zoneNum = int(ssn.nodeValue)
                                foundVal = True
                if not foundVal:
                    tkMessageBox.showinfo('zonetransform','Failed to find zone number, defaulting to 5')
                    zoneNum = 5
                else:
                    if Debug:
                        print 'Zone is',zoneNum
                        print 'Translates to',self.zmins[zoneNum-1],':',self.zmaxs[zoneNum-1],'m/s'

                # Need to build a new node.
                thisnode.setAttribute('xsi:type',u'CustomSpeedZone_t')
                vChild = dom1.createElement('ViewAs')
                try:
                    if thisnode.parentNode.parentNode.parentNode.getAttribute('Sport') == 'Running':
                        vaChild = dom1.createTextNode('Pace')
                    else:
                        vaChild = dom1.createTextNode('Speed')
                except Exception as e:
                    mstring= 'Exception '+str(e)+'encountered identifying workout sport.\n Defaulting to display as pace'
                    tkMessageBox.showerror('zonetransform',mstring)
                    vaChild = dom1.createTextNode('Pace')
                vChild.appendChild(vaChild)
                minChild = dom1.createElement('LowInMetersPerSecond')
                mintChild = dom1.createTextNode(self.zmins[zoneNum-1])
                minChild.appendChild(mintChild)
                maxChild = dom1.createElement('HighInMetersPerSecond')
                maxtChild = dom1.createTextNode(self.zmaxs[zoneNum-1])
                maxChild.appendChild(maxtChild)

                while thisnode.hasChildNodes():
                    x1 = thisnode.lastChild
                    thisnode.removeChild(thisnode.lastChild)
                    x1.unlink()
                thisnode.appendChild(vChild)
                thisnode.appendChild(minChild)
                thisnode.appendChild(maxChild)

        if not modified:
            tkMessageBox.showinfo('zonetransform','No changes made to input file '+self.fname+', output file not written')
        else:
            # find all Names which are children of Workouts; tcx files should contain
            # at least the Author node with a Name in, so don't just edit every Name you find
            # File may contain multiple workouts, so edit all names. In that case, not all
            # workouts may be *changed*, but if this file is loaded into GTC there is still scope
            # for clashing with existing names, so do it anyway.
            for thisnode in dom1.getElementsByTagName('Name'):
                # possible in principle to have no parent, so nodeName throws
                # AttributeError. Not a Workout's Name in that case, so try/except pass
                # is fine.
                try:
                    if thisnode.parentNode.nodeName == 'Workout':
                        for ssn in thisnode.childNodes:
                            if ssn.nodeName == '#text':
                                oldName = ssn.nodeValue
                                ssn.nodeValue = oldName+'cz'
                                if Debug:
                                    print oldName,ssn.nodeValue
                except:
                    pass

            (namein,extin) = os.path.splitext(self.fname)
            outname = namein+'cz'+extin
            badcount=0
            while os.path.exists(outname):
                badcount = badcount+1
                outname = namein+'cz'+str(badcount)+extin
                if Debug:
                    print badcount,outname
            with open(outname,'w') as xout:
                dom1.writexml(xout,addindent='  ',newl='\n')
            tkMessageBox.showinfo('zonetransform','Converted successfully as '+outname)
        if Debug:
            print 'done'
        self.buttonRun.configure(relief='raised')

    # interfaces to dialog for setting zones
    def setZonesCallback(self):
        self.buttonSetZones.configure(relief='sunken')
        newzones = setZones(rootWin,title='Select your pace zones').result
        if Debug:
            print newzones
        if newzones:
            self.refreshZones()
        self.buttonSetZones.configure(relief='raised')

    # called whenever ztZones is altered, to update the metres/second data which is
    # written to the tcx
    def refreshZones(self):
        txv = []
        self.zmins = []
        self.zmaxs = []

        # convert paces to metres/second
        # Shouldn't go wrong unless user has been editing the cfg file by hand
        if ztZ.distunit()=='m':
            scalefac = 1609.0
        elif ztZ.distunit()=='k':
            scalefac = 1000.0
        else:
            tkMessageBox.showerror('Bad distance unit',
                'Distance unit '+str(ztZ.distunit())+' must be m or k. Defaulting to km')
            scalefac = 1000.0
        for zstring in ztZ.zones():
            try:
                tx = zstring.split(':')
                txv.append(scalefac/(60.0*float(tx[0])+float(tx[1])))
            except:
                pass

        if len(txv) != 11: # includes trap for exception above
            tkMessageBox.showerror('zonetransform', 'Zones incorrect, should be a list of 11 paces')
            if Debug:
                print ztZ.zones()
            exit
        for loop in range(len(txv)-1):
            self.zmins.append("%.7f" % txv[loop])
            self.zmaxs.append("%.7f" % txv[loop+1])
        if Debug:
            print self.zmins
            print self.zmaxs

    def saveZonesCallback(self):
        global currwd
        self.buttonSaveZones.configure(relief='sunken')
        if not currwd:
            currwd = os.getcwd()
        if not self.sourcedir:
            tkMessageBox.showerror('Save zones failed',"Can't identify directory for zone config file")
            self.buttonSaveZones.configure(relief='raised')
            return
        try:
            os.chdir(self.sourcedir)
            if os.path.exists('ztconfig.cfg'):
                if os.path.isfile('ztconfig.cfg'):
                    if os.path.isfile('ztconfig.cfg1'):
                        os.unlink('ztconfig.cfg1')
                    os.rename('ztconfig.cfg','ztconfig.cfg1')
        except Exception as e:
            tkMessageBox.showerror('Save zones failed','Error '+str(e)+' creating zone config file')
            os.chdir(currwd)
            self.buttonSaveZones.configure(relief='raised')
            return
        try:
            with open('ztconfig.cfg','w') as ztcout:
                pickle.dump(ztZ.zones(),ztcout)
                pickle.dump(ztZ.distunit(),ztcout)
        except Exception as e:
            tkMessageBox.showerror('Save zones failed','Error '+str(e)+' writing zone config file')
        os.chdir(currwd)
        self.buttonSaveZones.configure(relief='raised')


    # Currently not callable, removed that button as zones always load automatically at startup
    def loadZonesCallback(self):
        self.buttonLoadZones.configure(relief='sunken')
        self.loadZones()
        self.buttonLoadZones.configure(relief='raised')

    def loadZones(self):
        global currwd
        global strzones
        if not currwd:
            currwd = os.getcwd()
        if not self.sourcedir:
            tkMessageBox.showerror('Load zones failed',"Can't identify directory for zone config file")
            return False
        try:
            os.chdir(self.sourcedir)
            if os.path.exists('ztconfig.cfg') and os.path.isfile('ztconfig.cfg'):
                with open('ztconfig.cfg','r') as ztcin:
                    a1 = pickle.load(ztcin)
                    a2 = pickle.load(ztcin)
                    try:
                        if len(a1) != 11 or (a2 != 'm' and a2 != 'k'):
                            tkMessageBox.showerror('Load zones failed','Zone file format incorrect')
                            os.chdir(currwd)
                            return False
                    except:
                        tkMessageBox.showerror('Load zones failed','Zone file format incorrect')
                        os.chdir(currwd)
                        return False
                    ztZ.setzones(a1)
                    ztZ.setdistunit(a2)
                    self.refreshZones()
            else:
                tkMessageBox.showinfo('Load zones failed','Saved zone file not found')
                os.chdir(currwd)
                return False
            if Debug:
                print len(a1)
                print a2
        except Exception as e:
            tkMessageBox.showerror('Load zones failed','Error '+str(e)+' reading zone config file')
            os.chdir(currwd)
            return False
        return True

    def exitCallback(self):
        self.myParent.destroy()

def main():
    # instantiate GUI
    global rootWin
    rootWin = Tkinter.Tk()
    zonetransformapp = zoneTransformApp(rootWin)
    rootWin.mainloop()

# end of main()
if __name__ == "__main__":
    main()
