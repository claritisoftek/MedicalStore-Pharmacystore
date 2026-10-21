import sys
if __name__ == '__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--self-test':
        from pharmacy.selftest import run
        sys.exit(run(sys.argv[2]))
    from pharmacy.app import main
    main()
